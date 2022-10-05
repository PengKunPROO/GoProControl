import argparse
import asyncio
import json
import os
import sys
import time
from binascii import hexlify
from bleak import BleakClient, BleakScanner
from rich.logging import RichHandler
from typing import Optional, Dict, Any
import logging
import Commonds
import requests
import pywifi
from pywifi import const
from UtilMath import get_max_group_media

FORMAT = "%(message)s"
logging.basicConfig(level='INFO', format=FORMAT, datefmt='[%X]', handlers=[RichHandler()])

logger = logging.getLogger('rich')
logger.setLevel('INFO')

current_client: BleakClient

wifi_profile = []

# It will be assigned to False if any command sent failed.
command_set_mark: bool = False


def connect_wifi_by_ssid(ssid, psw):
    scan_count = 10
    while scan_count:
        logger.info(f'scan for target wifi {ssid}   :{scan_count}')
        wifi = pywifi.PyWiFi()
        ifaces = wifi.interfaces()[0]
        ifaces.disconnect()
        ifaces.scan()
        time.sleep(3)
        wifi_info = ifaces.scan_results()
        find = False
        for wifi_ssid in wifi_info:
            if wifi_ssid.ssid == ssid:
                find = True
        if find:
            logger.info(f'Find the wifi named {ssid}')
            scan_count = 0
        else:
            scan_count -= 1

    ifaces.disconnect()
    time.sleep(3)
    # time.sleep(3)
    profile = pywifi.Profile()
    profile.ssid = ssid
    profile.auth = const.AUTH_ALG_OPEN
    profile.akm.append(const.AKM_TYPE_WPAPSK)
    profile.cipher = const.CIPHER_TYPE_CCMP
    profile.key = psw
    ifaces.remove_all_network_profiles()
    tmp_profile = ifaces.add_network_profile(profile)
    connect_count = 1
    while connect_count:
        logger.info(f'connect for target wifi {ssid}   :{connect_count}')
        ifaces.connect(tmp_profile)
        time.sleep(5)
        connect_count -= 1

    # 需要线程挂一下，3s够了，不然换wifi导致出错
    if ifaces.status() == const.IFACE_CONNECTED:
        logger.info(f'Connected to {ssid} successfully!')
    else:
        logger.info(f'Connected to {ssid} failed!')


def callback_while_connect(sender, data):
    logger.info(f'Sender:{sender}, Data:{data}')


async def scan():
    devices = await BleakScanner.discover()
    for device in devices:
        logger.info(f'Found:{device}')
    return devices


async def is_have_notify(client: BleakClient):
    def notification_handler(handle: int, data: bytes) -> None:
        logger.info(f'Received response at {handle=}: {hexlify(data, ":")}!r')
        if client.services.characteristics[handle].uuid == Commonds.Characteristics.CommandNotifications and data[
            2] == 0x00:
            logger.info('Command sent successfully!')
        else:
            logger.error('Unexpected response!')

    for service in client.services:
        for char in service.characteristics:
            if 'notify' in char.properties:
                await client.start_notify(char, callback=notification_handler)


async def is_have_stop_notify(client: BleakClient):
    for service in client.services:
        for char in service.characteristics:
            if 'notify' in char.properties:
                await client.stop_notify(char, callback=callback_while_connect)


# 这里缓存一下所有的GoPro的Wi-Fi信息，用于之后下载到本地
async def connect2wifi(client: BleakClient):
    global wifi_profile
    ssid = await client.read_gatt_char(Commonds.Characteristics.WifiAPSsidUid)
    ssid = ssid.decode()
    logger.info(f'SSID is {ssid}')
    password = await client.read_gatt_char(Commonds.Characteristics.WifiAPPasswordUuid)
    password = password.decode()
    logger.info(f'PassWord is {password}')
    await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic, Commonds.Commands.WiFi.OFF,
                                 response=True)
    await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic, Commonds.Commands.WiFi.ON,
                                 response=True)
    logger.info(f'wifi is enabled!')
    wifi_profile.append({'ssid': ssid, 'psw': password})


async def connect(client, camera, is_wifi_on: bool):
    try:
        logger.info(f'Camera {camera.get("target")} Connected!')
        await client.connect()
        await is_have_notify(client)
        if is_wifi_on:
            await connect2wifi(client)
    except Exception as e:
        logger.error(e)


async def disconnect(client, camera):
    try:
        await client.disconnect()
        await client.stop_notify(Commonds.Characteristics.ControlCharacteristic)
        logger.info(f'Camera {camera.get("target")} Disconnected!')
    except Exception as e:
        logger.error(e)


# wifi_list就是那个global wifi列表，里面存的都是字典
def download_file(wifi_list, paras):
    if paras.mode == 'video':
        for wifi in wifi_list:
            connect_wifi_by_ssid(wifi.get('ssid'), wifi.get('psw'))
            # 连上谁的wifi下载的就是哪个相机的文件
            media_list = get_media_list()
            max_timestamp: int = int(0)
            max_media = ''
            for media in [x for x in media_list['media'][0]['fs']]:
                if media['n'].lower().endswith('.mp4'):
                    temp = int(media['mod'])
                    if temp > max_timestamp:
                        max_timestamp = temp
                        max_media = media['n']

    elif paras.mode == 'photo':
        for indexx, wifi in enumerate(wifi_list):
            connect_wifi_by_ssid(wifi.get('ssid'), wifi.get('psw'))
            media_list = get_media_list()
            # 找时间戳前几大的jpg格式的文件，然后下载
            # media_find_list的长度=time_span=countdown
            media_find_list = []
            for media in [x for x in media_list['media'][0]['fs']]:
                if media['n'].lower().endswith('.jpg'):
                    media_find_list.append(media)
            download_url = Commonds.Characteristics.GoProBaseURL + Commonds.Commands.WiFi.DOWNLOAD_FIlE
            print('form the url:' + download_url)
            countdown = int(paras.time)
            media_res_list = get_max_group_media(media_find_list, countdown)
            print(media_res_list)
            for index in range(media_res_list.__len__()):
                if countdown <= 0:
                    break
                url = download_url + '/' + str(media_res_list[index]['n'])
                logger.info(f'Downloading {media_res_list[index]["n"]} from {download_url}')
                with requests.get(url, stream=True) as request:
                    request.raise_for_status()
                    # 命名方式： 文件总目录+wifi名+文件名
                    dir_in = paras.file[0] + '/' + wifi.get('ssid') + '/' + paras.mode
                    if not os.path.exists(dir_in):
                        os.makedirs(dir_in)
                    file = dir_in+'/'+media_res_list[index]['n'].split('.')[0]+'.jpg'
                    logger.info(f'file name is {file}')
                    with open(file, "wb") as f:
                        logger.info(f'Receiving binary stream to {file}...')
                        for chunk in request.iter_content(chunk_size=8192):
                            f.write(chunk)
                countdown -= 1


async def set_camera(client: BleakClient, camera, paload_in: Commonds.CapturePayLoad):
    if paload_in.capture_mode == Commonds.CaptureMode.PHOTO:
        logger.info(f'Camera {camera.get("target")} is setting to photo mode')
        await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic,
                                     Commonds.Commands.PresetGroups.Photo, response=True)
    elif paload_in.capture_mode == Commonds.CaptureMode.VIDEO:
        logger.info(f'Camera {camera.get("target")} is setting to video mode')
        await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic,
                                     Commonds.Commands.PresetGroups.Video, response=True)


async def record_video(client: BleakClient, camera, payload: Commonds.CapturePayLoad):
    if payload.capture_mode == Commonds.CaptureMode.PHOTO:
        for i in range(int(payload.time_span)):
            logger.info(f'Start photoing!')
            logger.info(f'Camera {camera.get("target")} is taking a photo')
            await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic,
                                         Commonds.Commands.Shutter.Start,
                                         response=True)
            await asyncio.sleep(int(payload.time_span))
            await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic, Commonds.Commands.Shutter.Stop,
                                         response=True)
    elif payload.capture_mode == Commonds.CaptureMode.VIDEO:
        logger.info(f'start recording!')
        logger.info(f'Camera {camera.get("target")} is Recording')
        await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic, Commonds.Commands.Shutter.Start,
                                     response=True)
        await asyncio.sleep(int(payload.time_span))
        await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic, Commonds.Commands.Shutter.Stop,
                                     response=True)
        # response = requests.get(Commonds.Characteristics.GoProBaseURL + Commonds.Commands.WIFIShutter.Stop)
        # response.raise_for_status()
        logger.info('Stop Command sent successfully!')


# 这个就同步进行吧，在拍完之后同步连接两个GoPro的wifi然后进行下载
def get_media_list() -> Dict[str, Any]:
    url = Commonds.Characteristics.GoProBaseURL + Commonds.Commands.WiFi.GET_MEDIA_LIST
    logger.info(f'getting the media list: sending {url}')
    response = requests.get(url)
    time.sleep(5)
    response.raise_for_status()
    logger.info('Get media Command sent sucdessfully!')

    # logger.info(f"Response: {json.dumps(response.json(), indent=4)}")

    return response.json()


def control_by_command(loop, camera_list, command_type: Optional[Commonds.CommandsType] = None, paras=None):
    if camera_list is None:
        global logger
        logger.error('Not found GoPro')
        return
    global tasks
    # one command only do one thing,so clear the whole tasks and add the same command type into it.
    tasks.clear()
    if command_type == Commonds.CommandsType.CONNECT:
        for camera in camera_list:
            tasks.append(loop.create_task(connect(camera.get('bleak_client'), camera, is_wifi_on=True),
                                          name=f'Connect {camera.get("target")}'))
    elif command_type == Commonds.CommandsType.DISCONNECT:
        for camera in camera_list:
            tasks.append(loop.create_task(disconnect(camera.get('bleak_client'), camera),
                                          name=f'Disconnect {camera.get("target")}'))
    elif command_type == Commonds.CommandsType.RECORD:
        if paras.mode == 'video':
            capture_payload = Commonds.CapturePayLoad(Commonds.CommandsType.RECORD, time_span=paras.time,
                                                      resolution=Commonds.VideoRes.LowRES,
                                                      mode=Commonds.CaptureMode.VIDEO)
        elif paras.mode == 'photo':
            capture_payload = Commonds.CapturePayLoad(Commonds.CommandsType.RECORD, time_span=paras.time,
                                                      resolution=Commonds.VideoRes.LowRES,
                                                      mode=Commonds.CaptureMode.PHOTO)
        for camera in camera_list:
            tasks.append(loop.create_task(record_video(camera.get('bleak_client'), camera, capture_payload),
                                          name=f'Connect {camera.get("target")}'))
    elif command_type == Commonds.CommandsType.PRESETS:
        if paras.mode == 'photo':
            capture_payload = Commonds.CapturePayLoad(Commonds.CommandsType.PRESETS, time_span=paras.time,
                                                      resolution=Commonds.VideoRes.LowRES,
                                                      mode=Commonds.CaptureMode.PHOTO)
        elif paras.mode == 'video':
            capture_payload = Commonds.CapturePayLoad(Commonds.CommandsType.PRESETS, time_span=paras.time,
                                                      resolution=Commonds.VideoRes.LowRES,
                                                      mode=Commonds.CaptureMode.VIDEO)
        for camera in camera_list:
            tasks.append(loop.create_task(set_camera(camera.get('bleak_client'), camera, capture_payload),
                                          name=f'Connect {camera.get("target")}'))


async def mainloop(loop, paras):
    camera_list = []
    global tasks
    found_devices = await loop.create_task(scan())
    # await asyncio.wait([found_devices,])
    # def notification_handler(handler: int, data: bytes, client: BleakClient) -> None:
    #     logger.info(f'Received response at {handler=}: {hexlify(data, ":")!r}')
    #     if client.services.characteristics[handler].uuid == Commonds.Characteristics.CommandNotifications and data[2] == 0x00:
    #         logger.info('Command sent successfully!')
    #     else:
    #         logger.error('Unexpected response!')
    #
    #     event.set()

    for device in found_devices:
        # char array
        device_arr = device.name.split(' ')
        if device_arr[0] == 'GoPro':
            camera_list.append({'target': f'{device_arr[0]} {device_arr[1]}',
                                'enable_wifi': False,
                                'address': f'{device.address}',
                                'bleak_client': BleakClient(device.address)}
                               )
    logger.info(camera_list)

    tasks.clear()
    control_by_command(loop, camera_list=camera_list, command_type=Commonds.CommandsType.CONNECT, paras=paras)
    await asyncio.wait(tasks)
    tasks.clear()
    control_by_command(loop, camera_list=camera_list, command_type=Commonds.CommandsType.PRESETS, paras=paras)
    await asyncio.wait(tasks)
    tasks.clear()
    control_by_command(loop, camera_list=camera_list, command_type=Commonds.CommandsType.RECORD, paras=paras)
    await asyncio.wait(tasks)
    dones, pendings = await asyncio.wait(tasks)
    print(dones, pendings)
    for task in dones:
        print("Task ret:", task.result())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GoPro Controller')
    parser.add_argument('-m', '--mode', help='模式选择，video和photo', default='photo')
    parser.add_argument('-t', '--time', help='记录时间，如果是photo就代表拍的张数', default='2')
    # 此命令行参数可以接收多个参数
    parser.add_argument('-f', '--file', nargs='+', help='相机存储位置', default=['/Users/pengkun/Desktop/GoProVideo/'])
    args = parser.parse_args()
    try:
        tasks = []
        loop_outer = asyncio.get_event_loop()
        task = loop_outer.create_task(mainloop(loop=loop_outer, paras=args))
        loop_outer.run_until_complete(asyncio.wait([task, ]))
        download_file(wifi_list=wifi_profile, paras=args)
        loop_outer.close()
    except Exception as e:
        logger.error(repr(e))
        sys.exit(-1)
    else:
        sys.exit(0)

import asyncio
import json
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

FORMAT = "%(message)s"
logging.basicConfig(level='INFO', format=FORMAT, datefmt='[%X]', handlers=[RichHandler()])

logger = logging.getLogger('rich')
logger.setLevel('INFO')

current_client: BleakClient

wifi_profile = []


def connect_wifi_by_ssid(ssid, psw):
    wifi = pywifi.PyWiFi()
    ifaces = wifi.interfaces()[0]
    # ifaces.disconnect()
    # time.sleep(3)

    profile = pywifi.Profile()
    profile.ssid = ssid
    profile.auth = const.AUTH_ALG_OPEN
    profile.key = psw

    tmp_profile = ifaces.add_network_profile(profile)
    ifaces.connect(tmp_profile)
    # 需要线程挂一下，3s够了，不然换wifi导致出错
    time.sleep(3)
    if ifaces.status() == const.IFACE_CONNECTED:
        logger.info(f'Connected to {ssid} successfully!')
    else:
        logger.info(f'Connected to {ssid} failed!')


def notification_handler(handle: int, data: bytes, client: BleakClient) -> None:
    logger.info(f'Received response at {handle=}: {hexlify(data, ":")}!r')
    if client.services.characteristics[handle].uuid == Commonds.Characteristics.CommandNotifications and data[
        2] == 0x00:
        logger.info('Command sent successfully!')
    else:
        logger.error('Unexpected response!')


def callback_while_connect(sender, data):
    logger.info(f'Sender:{sender}, Data:{data}')


async def scan():
    devices = await BleakScanner.discover()
    for device in devices:
        logger.info(f'Found:{device}')
    return devices


async def is_have_notify(client: BleakClient):
    for service in client.services:
        for char in service.characteristics:
            if 'notify' in char.properties:
                await client.start_notify(char, callback=callback_while_connect)


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
def download_file(wifi_list):
    for wifi in wifi_list:
        connect_wifi_by_ssid(wifi.get('ssid'), wifi.get('psw'))
        # 连上谁的wifi下载的就是哪个相机的文件
        media_list = get_media_list()
        max_timestamp = 0
        max_media = ''
        for media in [x for x in media_list['media'][0]['fs']]:
            print(media['mod'])
            temp = int(media['mod'])
            if temp > max_timestamp:
                max_timestamp = media['mod']
                max_media = media['n']

        print(max_media)


async def record_video(client: BleakClient, camera, payload: Commonds.CapturePayLoad):
    logger.info(f'start recording!')
    # response = requests.get(Commonds.Characteristics.GoProBaseURL + Commonds.Commands.WIFIShutter.Start)
    # response.raise_for_status()
    # logger.info('Command sent successfully!')
    logger.info(f'Camera {camera.get("target")} is Recording')
    await client.write_gatt_char(Commonds.Characteristics.ControlCharacteristic, Commonds.Commands.Shutter.Start,
                                 response=True)
    await asyncio.sleep(payload.time_span)
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
    response.raise_for_status()
    logger.info('Command sent sucdessfully!')

    logger.info(f"Response: {json.dumps(response.json(), indent=4)}")

    return response.json()


def control_by_command(loop, camera_list, command_type: Optional[Commonds.CommandsType] = None):
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
    elif command_type == Commonds.CommandsType.VIDEO:
        capture_payload = Commonds.CapturePayLoad(Commonds.CommandsType.VIDEO, time_span=3)
        for camera in camera_list:
            tasks.append(loop.create_task(record_video(camera.get('bleak_client'), camera, capture_payload),
                                          name=f'Connect {camera.get("target")}'))
    elif command_type == Commonds.CommandsType.PHOTO:
        pass
    elif command_type == Commonds.CommandsType.PRESETS:
        pass


async def main(loop):
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

    # while True:
    #     key_value = input()
    #     if key_value == 'g':
    #         control_by_command(loop, camera_list=camera_list, command_type=Commonds.CommandsType.VIDEO)
    #     elif key_value == 'c':
    #         control_by_command(loop, camera_list=camera_list, command_type=Commonds.CommandsType.CONNECT)
    #     elif key_value == 'd':
    #         control_by_command(loop, camera_list=camera_list, command_type=Commonds.CommandsType.DISCONNECT)
    #     elif key_value == 'q':
    #         break
    tasks.clear()
    control_by_command(loop, camera_list=camera_list, command_type=Commonds.CommandsType.CONNECT)
    await asyncio.wait(tasks)
    # control_by_command(loop, camera_list=camera_list, command_type=Commonds.CommandsType.VIDEO)
    dones, pendings = await asyncio.wait(tasks)
    print(dones, pendings)
    for task in dones:
        print("Task ret:", task.result())
    download_file(wifi_profile)


tasks = []
loop_outer = asyncio.get_event_loop()
loop_outer.run_until_complete(main(loop_outer))
loop_outer.close()
# download_file(wifi_profile)

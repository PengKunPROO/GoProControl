from typing import Optional
from enum import Enum

BLE_CHAR_STRING = "0000{}-0000-1000-8000-00805f9b34fb"
BLE_CHAR_V2_STRING = "{}-aa8d-11e3-9046-0002a5d5c51b"


class CommandsType(Enum):
    CONNECT = 0
    DISCONNECT = 1
    VIDEO = 2
    PHOTO = 3
    # preset the goPro's properties, like resolution, night photo and etc...
    PRESETS = 4


class Commands:
    class Shutter:
        Start = bytearray(b'\x03\x01\x01\x01')
        Stop = bytearray(b'\x03\x01\x01\x00')

    class WIFIShutter:
        Start = f'/gopro/camera/shutter/start'
        Stop = f'/gopro/camera/shutter/stop'
    class Mode:
        Video = bytearray(b'\x03\x02\x01\x00')
        Photo = bytearray(b'\x03\x02\x01\x01')
        Multishot = bytearray(b'\x03\x02\x01\x02')

    class Submode:
        class Video:
            Single = bytearray(b'\x05\x03\x01\x00\x01\x00')
            TimeLapse = bytearray(b'\x05\x03\x01\x00\x01\x01')

        class Photo:
            Single = bytearray(b'\x05\x03\x01\x01\x01\x01')
            Night = bytearray(b'\x05\x03\x01\x01\x01\x02')

        class Multishot:
            Burst = bytearray(b'\x05\x03\x01\x02\x01\x00')
            TimeLapse = bytearray(b'\x05\x03\x01\x02\x01\x01')
            NightLapse = bytearray(b'\x05\x03\x01\x02\x01\x02')

    class Basic:
        PowerOff = bytearray(b'\x01\x05')
        PowerOffForce = bytearray(b'\x01\x04')
        HiLightTag = bytearray(b'\x01\x18')

    class Locate:
        ON = bytearray(b'\x03\x16\x01\x01')
        OFF = bytearray(b'\x03\x16\x01\x00')

    class WiFi:
        ON = bytearray(b'\x03\x17\x01\x01')
        OFF = bytearray(b'\x03\x17\x01\x00')
        GET_MEDIA_LIST = '/gopro/media/list'

    # OpenGoPro commands
    class Presets:
        Activity = bytearray(b'\x06\x40\x04\x00\x00\x00\x01')
        BurstPhoto = bytearray(b'\x06\x40\x04\x00\x01\x00\x02')
        Cinematic = bytearray(b'\x06\x40\x04\x00\x00\x00\x02')
        LiveBurst = bytearray(b'\x06\x40\x04\x00\x01\x00\x01')
        NightPhoto = bytearray(b'\x06\x40\x04\x00\x01\x00\x03')
        NightLapse = bytearray(b'\x06\x40\x04\x00\x02\x00\x02')
        Photo = bytearray(b'\x06\x40\x04\x00\x01\x00\x00')
        SloMo = bytearray(b'\x06\x40\x04\x00\x00\x00\x03')
        Standard = bytearray(b'\x06\x40\x04\x00\x00\x00\x00')
        TimeLapse = bytearray(b'\x06\x40\x04\x00\x02\x00\x01')
        TimeWarp = bytearray(b'\x06\x40\x04\x00\x02\x00\x00')
        MaxPhoto = bytearray(b'\x06\x40\x04\x00\x04\x00\x00')
        MaxTimewarp = bytearray(b'\x06\x40\x04\x00\x05\x00\x00')
        MaxVideo = bytearray(b'\x06\x40\x04\x00\x03\x00\x00')

    class PresetGroups:
        Video = bytearray(b'\x04\x3E\x02\x03\xE8')
        Photo = bytearray(b'\x04\x3E\x02\x03\xE9')
        Timelapse = bytearray(b'\x04\x3E\x02\x03\xEA')

    class Turbo:
        ON = bytearray(b'\x04\xF1\x6B\x08\x01')
        OFF = bytearray(b'\x04\xF1\x6B\x08\x00')

    class Analytics:
        SetThirdPartyClient = bytearray(b'\x01\x50')


class Characteristics:
    Control = BLE_CHAR_STRING.format("FEA6".lower())
    Info = BLE_CHAR_STRING.format("180A".lower())
    Battery = BLE_CHAR_STRING.format("180F".lower())

    FirmwareVersion = BLE_CHAR_STRING.format("2A26".lower())
    SerialNumber = BLE_CHAR_STRING.format("2A25".lower())
    BatteryLevel = BLE_CHAR_STRING.format("2A19".lower())

    ControlCharacteristic = BLE_CHAR_V2_STRING.format("B5F90072".lower())
    SettingCharacteristic = BLE_CHAR_V2_STRING.format("B5F90074".lower())

    CommandNotifications = BLE_CHAR_V2_STRING.format("B5F90073".lower())
    SettingNotifications = BLE_CHAR_V2_STRING.format("B5F90075".lower())

    StatusCharacteristic = BLE_CHAR_V2_STRING.format("B5F90076".lower())
    StatusNotifications = BLE_CHAR_V2_STRING.format("B5F90077".lower())

    WifiAPSsidUid = BLE_CHAR_V2_STRING.format("B5F90002".lower())
    WifiAPPasswordUuid = BLE_CHAR_V2_STRING.format("B5F90003".lower())
    GoProBaseURL = 'http://10.5.5.9:8080'


class CapturePayLoad:
    def __init__(self, command_type: CommandsType, time_span: Optional[float]):
        self.command_type = command_type
        # if time_span is null,then the default mode is photo
        self.time_span = time_span

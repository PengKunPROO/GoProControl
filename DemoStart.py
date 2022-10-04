import time
from open_gopro import GoPro, Params
from rich.console import Console
from open_gopro.util import setup_logging
from typing import Tuple, Optional
from bleak import BleakScanner, BleakClient
from bleak import discover
from open_gopro import constants
import logging

console = Console()
logger = logging.getLogger()
logger = setup_logging(logger, "/Users/pengkun/Desktop/GoProLogger/log.rft")

gopro: Optional[GoPro] = None
return_code = 0
try:
    with GoPro() as gopro:
        # Configure settings to prepare for video
        if gopro.is_encoding:
            assert gopro.ble_command.set_shutter(Params.Shutter.OFF).is_ok
        #assert gopro.ble_setting.video_performance_mode.set(Params.PerformanceMode.MAX_PERFORMANCE).is_ok
        assert gopro.ble_setting.max_lens_mode.set(Params.MaxLensMode.DEFAULT).is_ok
        assert gopro.ble_command.set_turbo_mode(False).is_ok
        assert gopro.ble_setting.resolution.set(Params.Resolution.RES_1080).is_ok
        assert gopro.ble_command.load_preset(Params.Preset.CINEMATIC).is_ok

        # Get the media list before
        media_set_before = set(x["n"] for x in gopro.wifi_command.get_media_list().flatten)
        # Take a video
        console.print("Capturing a video...")
        assert gopro.ble_command.set_shutter(Params.Shutter.ON).is_ok
        time.sleep(10)
        assert gopro.ble_command.set_shutter(Params.Shutter.OFF).is_ok

        # Get the media list after
        media_set_after = set(x["n"] for x in gopro.wifi_command.get_media_list().flatten)
        # The video (is most likely) the difference between the two sets
        video = media_set_after.difference(media_set_before).pop()
        # Download the video
        console.print("Downloading the video...")
        output_location = "/Users/pengkun/Desktop/GoProVideo/m_VideoTest"
        gopro.wifi_command.download_file(camera_file=video, local_file=output_location)
        console.print(f"Success!! :smiley: File has been downloaded to {output_location}")

except KeyboardInterrupt:
    logger.warning("Received keyboard interrupt. Shutting down...")
if gopro is not None:
    gopro.close()
console.print("Exiting...")
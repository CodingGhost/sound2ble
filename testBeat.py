
import asyncio
import logging
import BeatDetection.BeatDetector as bd

logging.getLogger("BeatDetector").setLevel(logging.WARNING)  # Options: DEBUG, INFO, WARNING, ERROR
logging.getLogger("AudioProcessing").setLevel(logging.WARNING)
logging.getLogger("MadmomProcessor").setLevel(logging.WARNING)
logging.getLogger("BeatClassification").setLevel(logging.WARNING)

async def async_beat_callback():
    print("🔴 Beat detected!")


async def main():
    loop = asyncio.get_running_loop()
    detector = bd.BeatDetector(callback=async_beat_callback, loop=loop)
    detector.run()

    try:
        while True:
            await asyncio.sleep(1)  # Keep event loop running
    except KeyboardInterrupt:
        detector.stop()

asyncio.run(main())

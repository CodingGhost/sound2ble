import asyncio
import logging
from bleak import BleakScanner
from ble2led import Ble2Led

# Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("DMXController")

DEVICE_FILTER = ["b2l", "b2s"]

class BleController:
    """Manages DMX Devices and provides hardware abstraction."""

    def __init__(self):
        self.devices = {}

    async def findDevices(self):
        """Scan for DMX devices and return matching names."""
        log.info("Scanning for DMX devices...")
        found_devices = []
        devices = await BleakScanner.discover()

        for device in devices:
            if any(filter_name in (device.name or "") for filter_name in DEVICE_FILTER):
                found_devices.append(device.name)
                self.devices[device.name] = device.address

        return found_devices

    def getDevice(self, deviceName):
        """Returns a `Ble2Led` instance if the device exists."""
        if deviceName not in self.devices:
            raise ValueError("Device not found. Run findDevices() first.")
        return Ble2Led(self.devices[deviceName], deviceName)

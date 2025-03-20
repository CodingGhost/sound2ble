import asyncio
import logging
from bleak import BleakClient

log = logging.getLogger("BLEDevice")

DMX_SERVICE_UUID = "0000C001-0000-1000-8000-00805F9B34FB"
DMX_RX_CHAR_UUID = "0000C002-0000-1000-8000-00805F9B34FB"

class BLEDevice:
    """Represents a generic BLE device."""

    def __init__(self, address, name):
        self.address = address
        self.name = name
        self.client = None

    async def connect(self):
        """Connect to the BLE device."""
        log.info(f"Connecting to {self.name} ({self.address})...")
        self.client = BleakClient(self.address)
        await self.client.connect()
        log.info(f"Connected to {self.name}")

    async def disconnect(self):
        """Disconnect from the BLE device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            log.info(f"Disconnected from {self.name}")

    async def getRssi(self):
        """Retrieve RSSI value."""
        if self.client and self.client.is_connected:
            return await self.client.read_rssi()
        return None

    def getName(self):
        """Returns the device name."""
        return self.name

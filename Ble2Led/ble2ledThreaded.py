import asyncio
import logging
import threading
import queue
from .ble_device import BLEDevice

log = logging.getLogger("Ble2Led")

DMX_SERVICE_UUID = "0000C001-0000-1000-8000-00805F9B34FB"
DMX_RX_CHAR_UUID = "0000C002-0000-1000-8000-00805F9B34FB"

class Ble2Led(BLEDevice):
    """Manages a BLE LED device with optimized DMX transmission and smart batching."""

    def __init__(self, address, name):
        super().__init__(address, name)
        self.data = bytearray(10)  # 10-channel DMX buffer
        self.highest_changed_index = -1  # Track highest changed index
        self.dirty_flag = False  # Track if updates are pending
        self.debounce_delay = 0.002  # 2ms debounce

        # Threaded BLE Write System
        self.ble_queue = queue.Queue()
        self.ble_thread = threading.Thread(target=self._ble_worker, daemon=True)
        self.ble_thread.start()

    def updateDmx(self, index, value):
        """Update a DMX channel and queue BLE writes in a separate thread."""
        if not (0 <= index < 10):
            raise ValueError("DMX index must be between 0-9.")

        if not (0 <= value <= 255):
            raise ValueError("DMX values must be between 0-255.")

        if self.data[index] != value:
            self.data[index] = value
            self.highest_changed_index = max(self.highest_changed_index, index)
            self.dirty_flag = True  # Mark changes as pending

            # Queue the update (debounce + write in worker thread)
            self.ble_queue.put(None)

    def getDmx(self, index=None):
        """Get the DMX state (either all channels or a single one)."""
        if index is None:
            return self.data[:]  # Return a copy of all 10 bytes
        elif 0 <= index < 10:
            return self.data[index]
        else:
            raise ValueError("DMX index must be between 0-9.")

    def _ble_worker(self):
        """Worker thread that processes BLE writes in the background."""
        while True:
            try:
                self.ble_queue.get()  # Wait for update request
                asyncio.run(self._debounce_write())  # Run async BLE write in thread
            except Exception as e:
                log.error(f"BLE Worker Error: {e}")

    async def _debounce_write(self):
        """Wait briefly to batch multiple updates into a single BLE write."""
        await asyncio.sleep(self.debounce_delay)  # Wait for more changes

        if self.client and self.client.is_connected and self.dirty_flag and self.highest_changed_index >= 0:
            packet = self.data[: self.highest_changed_index + 1]
            await self.client.write_gatt_char(DMX_RX_CHAR_UUID, packet, response=False)
            log.debug(f"Sent: {list(packet)}")

            # Reset tracking variables
            self.highest_changed_index = -1
            self.dirty_flag = False

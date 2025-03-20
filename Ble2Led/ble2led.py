import asyncio
import logging
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
        self.debounce_task = None  # Track debounce task
        self.debounce_delay = 0.002  # 2ms debounce

    def updateDmx(self, index, value):
        """Update a DMX channel and ensure changes are batched into a single transmission."""
        if not (0 <= index < 10):
            raise ValueError("DMX index must be between 0-9.")

        if not (0 <= value <= 255):
            raise ValueError("DMX values must be between 0-255.")

        if self.data[index] != value:
            self.data[index] = value
            self.highest_changed_index = max(self.highest_changed_index, index)
            self.dirty_flag = True  # Mark that changes are pending

            # Restart the debounce timer (cancel old task if running)
            if self.debounce_task:
                self.debounce_task.cancel()

            self.debounce_task = asyncio.create_task(self._debounce_write())

    def getDmx(self, index=None):
        """Get the DMX state (either all channels or a single one)."""
        if index is None:
            return self.data[:]  # Return a copy of all 10 bytes
        elif 0 <= index < 10:
            return self.data[index]
        else:
            raise ValueError("DMX index must be between 0-9.")

    async def _debounce_write(self):
        """Waits briefly to batch multiple updates into a single BLE write."""
        try:
            await asyncio.sleep(self.debounce_delay)  # Wait for more changes

            if self.client and self.client.is_connected and self.dirty_flag and self.highest_changed_index >= 0:
                packet = self.data[: self.highest_changed_index + 1]
                await self.client.write_gatt_char(DMX_RX_CHAR_UUID, packet, response=False)
                log.debug(f"Sent: {list(packet)}")

                # Reset tracking variables
                self.highest_changed_index = -1
                self.dirty_flag = False
                self.debounce_task = None  # Allow new debounce task to start

        except asyncio.CancelledError:
            # If the task was cancelled, do nothing (new update will trigger another debounce)
            pass

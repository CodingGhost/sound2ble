import asyncio
import sys
import logging
from bleak import BleakClient, BleakScanner
import BeatDetection.BeatDetector as bd

# Workaround for Windows BLE async bug
sys.coinit_flags = 0  # 0 means MTA
try:
    from bleak.backends.winrt.util import allow_sta
    allow_sta()  # Required for BLE on Windows GUI applications
except ImportError:
    pass  # Other OSes or older Bleak versions will ignore this

# UUIDs for BLE communication
DMX_SERVICE_UUID = "0000C001-0000-1000-8000-00805F9B34FB"
DMX_RX_CHAR_UUID = "0000C002-0000-1000-8000-00805F9B34FB"

# Connection interval: The device requests 7.5ms intervals, so we optimize latency
CONN_INTERVAL_MS = 7.5 / 1000  # Convert to seconds

# Example data packet (r, g, b, dimmer, strobe)
DMX_PACKET = bytes([255, 255, 255, 200, 0])  # Modify as needed

logging.getLogger("BeatDetector").setLevel(logging.WARNING)  # Options: DEBUG, INFO, WARNING, ERROR
logging.getLogger("AudioProcessing").setLevel(logging.WARNING)
logging.getLogger("MadmomProcessor").setLevel(logging.WARNING)
logging.getLogger("BeatClassification").setLevel(logging.WARNING)

class DMXController:
    """Handles BLE communication for DMX lighting control."""

    def __init__(self):
        """Initialize the BLE client and event loop."""
        self.client = None
        self.device = None

    async def find_device(self):
        """Scan for BLE devices and allow user selection."""
        print("Scanning for BLE devices...")
        devices = await BleakScanner.discover()

        if not devices:
            print("No devices found.")
            sys.exit(1)

        print("\nSelect a device to connect:")
        for i, device in enumerate(devices):
            device_name = device.name if device.name else "Unknown Device"
            print(f"{i}: {device_name} ({device.address})")

        while True:
            try:
                selection = int(input("Enter the number of the device: "))
                if 0 <= selection < len(devices):
                    self.device = devices[selection]
                    return
                else:
                    print("Invalid selection, try again.")
            except ValueError:
                print("Please enter a valid number.")

    async def connect(self):
        """Connect to the selected BLE device."""
        if self.device is None:
            await self.find_device()

        self.client = BleakClient(self.device.address)
        await self.client.connect()
        print(f"Connected to {self.device.name} ({self.device.address})")

    async def disconnect(self):
        """Disconnect from the BLE device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("Disconnected from BLE device.")

    async def send_dmx_data(self, packet: bytes):
        """Send a DMX packet with low latency."""
        if not self.client or not self.client.is_connected:
            print("BLE not connected. Reconnecting...")
            await self.connect()

        try:
            await self.client.write_gatt_char(DMX_RX_CHAR_UUID, packet, response=False)
            await asyncio.sleep(CONN_INTERVAL_MS)  # Maintain low latency
        except Exception as e:
            print(f"Error writing data: {e}")

flag = False
async def async_beat_callback():
    """Handles beat detection event and sends a DMX signal."""
    global flag
    print("🔴 Beat detected!")
    if flag == True:
        print("test")
        await dmx_controller.send_dmx_data( bytes([255, 255, 255, 255, 0]) )  # Now simply call with packet
    else:
        await dmx_controller.send_dmx_data( bytes([0, 0, 0, 0, 0]) )
    flag = not flag
    


async def main():
    """Main function for BLE communication and Beat Detection."""
    global dmx_controller
    dmx_controller = DMXController()

    # Connect to BLE
    await dmx_controller.connect()

    # Start beat detection
    loop = asyncio.get_running_loop()
    detector = bd.BeatDetector(callback=async_beat_callback, loop=loop)
    detector.run()

    try:
        while True:
            await asyncio.sleep(1)  # Keep the event loop running
    except asyncio.CancelledError:
        print("Process cancelled.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        await dmx_controller.disconnect()  # Ensure cleanup on exit


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nUser interrupted, exiting.")

import sys
import asyncio
import json
import logging
import os
from tkinter import Tk, filedialog
from Ble2Led.ble_controller import BleController
from Ble2Led.ble2ledThreaded import Ble2Led
from Ble2Led.b2l_single import b2lSingle
import BeatDetection.BeatDetector as bd

# Workaround for Windows BLE async bug
sys.coinit_flags = 0  # 0 means MTA
try:
    from bleak.backends.winrt.util import allow_sta
    allow_sta()  # Required for BLE on Windows GUI applications
except ImportError:
    pass  # Other OSes or older Bleak versions will ignore this

logging.getLogger("Ble2Led").setLevel(logging.DEBUG)

class DMXBeatController:
    """Automatically connects to DMX BLE devices and syncs lights to beats."""

    def __init__(self):
        self.dmx_controller = BleController()
        self.connected_devices = []  # Stores a list of b2lSingle instances
        self.lighting_steps = []
        self.current_step = 0
        self.useBeat = True

    async def discover_devices(self):
        """Scans for available BLE DMX devices and connects to them."""
        devices = await self.dmx_controller.findDevices()

        if not devices:
            print("No DMX devices found.")
            return False

        print("\nFound DMX Devices:")
        for i, device in enumerate(devices):
            print(f"{i}: {device}")

        # Auto-connect to all found devices
        for device_name in devices:
            ble_device = self.dmx_controller.getDevice(device_name)
            dmx = Ble2Led(ble_device.address, ble_device.name)
            await dmx.connect()

            # Add both CH1 and CH2 as separate controllable devices
            self.connected_devices.append(b2lSingle(dmx, 0))  # CH1
            self.connected_devices.append(b2lSingle(dmx, 1))  # CH2

        print(f"✅ Connected to {len(self.connected_devices)} logical devices.")
        return True

    def load_json_file(self):
        """Prompts the user to select a JSON file and loads lighting steps."""
        root = Tk()
        root.withdraw()  # Hide the root window
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])

        if not file_path:
            print("❌ No file selected.")
            return False

        with open(file_path, "r") as f:
            data = json.load(f)

        if data.get("type") != "ble2led" or "steps" not in data:
            print("❌ Invalid JSON format.")
            return False

        self.lighting_steps = data["steps"]
        print(f"✅ Loaded {len(self.lighting_steps)} lighting steps from {os.path.basename(file_path)}")
        return True

    async def apply_lighting_step(self):
        """Sets all lights according to the current lighting step."""
        if not self.lighting_steps:
            print("⚠ No lighting steps loaded.")
            return

        step = self.lighting_steps[self.current_step]  # Get the current step
        for i, device_data in enumerate(step):
            device_id = device_data["id"] - 1  # Convert to zero-based index
            # If the ID is out of range, ignore it
            if device_id >= len(self.connected_devices):
                continue
            # If there are fewer JSON entries than devices, reuse ID=1 (device index 0)
            device = self.connected_devices[device_id] if device_id < len(self.connected_devices) else self.connected_devices[0]
            device.setRGB(device_data["r"], device_data["g"], device_data["b"])
            device.setDim(device_data["d"])
            device.setStrobe(device_data["s"])

        # Move to the next step (looping back to start if needed)
        print((self.current_step + 1))
        self.current_step = (self.current_step + 1) % len(self.lighting_steps)

    
    async def run(self):
        """Main execution loop: Discover devices, load JSON, and wait for beats."""
        print("\n🔍 Discovering DMX devices...")
        if not await self.discover_devices():
            return

        print("\n📂 Select a JSON file with lighting steps...")
        if not self.load_json_file():
            return

        print("\n🎵 Waiting for beats to trigger lighting changes...")
        loop = asyncio.get_running_loop()
        detector = bd.BeatDetector(callback=self.on_beat_detected, vuCallback=self.onVuUpdate, loop=loop)
        detector.run()

        try:
            while True:
                await asyncio.sleep(1)  # Keep the program alive
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
            bd.stop()
            await self.cleanup()

    def vu_to_led(self, vu_db):
        """Convert VU level (dB) to an LED brightness value (0-255)."""
        try:
            min_db, max_db = -50, -10  # Ensure valid range
            vu_db = max(min_db, min(max_db, vu_db))  # Clamp values
            led_value = int(((vu_db - min_db) / (max_db - min_db)) * 255)
            return led_value
        except Exception as e:
            print(f"Error in vu_to_led: {e}")
            return 0  # Return default value on failure



    # async def onVuUpdate(self, vu):
    #     """Triggered on each VU update - can be used for debugging."""
    #     try:
    #         val = self.vu_to_led(vu)  # Potentially problematic line
    #         print("test")  # Should be printed if function works
    #     except Exception as e:
    #         print(f"Error in vu_to_led: {e}")  # Catch exceptions

    async def onVuUpdate(self, vu):
        """Triggered on each VU update - can be used for debugging."""
        val = self.vu_to_led(vu)
        #print(f"🔊 VU: {val}")
        #device.setRGB(255, 255, 255)
        #device.setStrobe(device_data["s"])
        if not self.useBeat:
            for device in self.connected_devices:
                print("set dimmer to " + str(val))
                device.setRGB(255, 180, 100)
                device.setDim(val)
                


    async def on_beat_detected(self, isBeat):
        """Triggered on each beat - applies the next lighting step."""
        if(isBeat):
            self.useBeat = True
            print(f"🎶 Beat detected! Applying step {self.current_step + 1}/{len(self.lighting_steps)}")
            await self.apply_lighting_step()
        else:
            self.useBeat = False
            print("Lichtorgel")

    async def cleanup(self):
        """Disconnect all BLE devices before exiting."""
        for dmx in self.connected_devices:
            await dmx.ble2led.disconnect()
        print("✅ All devices disconnected.")




# Run the main program
if __name__ == "__main__":
    asyncio.run(DMXBeatController().run())

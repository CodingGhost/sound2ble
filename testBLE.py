import asyncio
from Ble2Led.ble_controller import BleController
from Ble2Led.ble2led import Ble2Led
from Ble2Led.b2l_single import b2lSingle
import logging

logging.getLogger("Ble2Led").setLevel(logging.DEBUG)

async def main():
    """Main demo function for controlling DMX lights."""

    # 1️⃣ Create a DMXController instance
    ble_controller = BleController()

    # 2️⃣ Scan for DMX-compatible devices
    devices = await ble_controller.findDevices()
    
    if not devices:
        print("No DMX devices found.")
        return

    print("\nFound DMX Devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device}")

    # 3️⃣ User selects a device
    selected_device = int(input("Select a device to connect: "))
    device_name = devices[selected_device]
    
    # 4️⃣ Get a BLEDevice instance from DmxController
    ble_device = ble_controller.getDevice(device_name)

    # 5️⃣ Convert BLEDevice → Ble2Led
    dmx = Ble2Led(ble_device.address, ble_device.name)

    # 6️⃣ Get logical device handlers
    led1 = b2lSingle(dmx, 0)  # CH1 LED
    led2 = b2lSingle(dmx, 1)  # CH2 LED

    # 7️⃣ Connect to the BLE device
    await dmx.connect()

    try:
        print("\n🚀 Running DMX Demo. Press Ctrl+C to exit.\n")

        sequence = [
            (led1, (255, 0, 0)),  # CH1 RED
            (led1, (0, 255, 0)),  # CH1 GREEN
            (led1, (0, 0, 255)),  # CH1 BLUE
            (led2, (255, 0, 0)),  # CH2 RED
            (led2, (0, 255, 0)),  # CH2 GREEN
            (led2, (0, 0, 255)),  # CH2 BLUE
        ]

        # 8️⃣ Turn ON LEDs in sequence
        print("set dim")
        led1.setDim(255)  # Set maximum brightness
        led2.setDim(255)  # Set maximum brightness
        print("set dim complete")
        for led, color in sequence:
            led.setRGB(*color)
            await asyncio.sleep(1)  # 1-second delay between color changes
        print("Sequence complete.")
        # 9️⃣ Turn OFF LEDs
        led1.setRGB(0, 0, 0)
        led2.setRGB(0, 0, 0)

    except KeyboardInterrupt:
        print("\nStopping demo...")

    finally:
        # 🔟 Disconnect all devices on exit
        await dmx.disconnect()
        print("Demo finished. Devices disconnected.")

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())

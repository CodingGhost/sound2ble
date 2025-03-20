from .ble2led import Ble2Led
from .led_interface import LEDInterface

class b2lSingle(LEDInterface):
    """Represents a single LED channel (CH1 or CH2) of a Ble2Led device."""

    def __init__(self, ble2led: Ble2Led, ch: int):
        if ch not in [0, 1]:
            raise ValueError("Channel must be 0 (CH1) or 1 (CH2).")

        self.ble2led = ble2led
        self.channel_offset = ch * 5  # CH1 = 0-4, CH2 = 5-9

    def setR(self, value):
        self.ble2led.updateDmx(self.channel_offset + 0, value)

    def getR(self):
        return self.ble2led.getDmx(self.channel_offset + 0)

    def setG(self, value):
        self.ble2led.updateDmx(self.channel_offset + 1, value)

    def getG(self):
        return self.ble2led.getDmx(self.channel_offset + 1)

    def setB(self, value):
        self.ble2led.updateDmx(self.channel_offset + 2, value)

    def getB(self):
        return self.ble2led.getDmx(self.channel_offset + 2)

    def setDim(self, value):
        self.ble2led.updateDmx(self.channel_offset + 3, value)

    def getDim(self):
        return self.ble2led.getDmx(self.channel_offset + 3)
    
    def setStrobe(self, value):
        self.ble2led.updateDmx(self.channel_offset + 4, value)

    def getSTrobe(self):
        return self.ble2led.getDmx(self.channel_offset + 4)

    def setRGB(self, r, g, b):
        self.setR(r)
        self.setG(g)
        self.setB(b)

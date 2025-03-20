from abc import ABC, abstractmethod

class LEDInterface(ABC):
    """Defines LED control functions."""

    @abstractmethod
    def setR(self, value): pass

    @abstractmethod
    def setG(self, value): pass

    @abstractmethod
    def setB(self, value): pass

    @abstractmethod
    def setDim(self, value): pass

    @abstractmethod
    def setRGB(self, r, g, b): pass

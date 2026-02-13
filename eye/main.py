import gc
import time
import machine
import dotmatrix

gc.collect()
gc.enable()

led = machine.Pin(2, machine.Pin.OUT)
spi = machine.SPI(2, baudrate=10000000, polarity=1, phase=0, sck=machine.Pin(18), mosi=machine.Pin(23))
cs = machine.Pin(5, machine.Pin.OUT)
display = dotmatrix(spi, cs, 4)

display.brightness(5)
display.clear()
display.show()

display.text("SONA")
display.show()

while True:
    led.value(1)
    time.sleep(0.5)
    led.value(0)
    time.sleep(0.5)

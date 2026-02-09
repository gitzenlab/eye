import gc
import machine
import time

gc.collect()
gc.enable()


led = machine.Pin(2, machine.Pin.OUT)

while True:
    led.value(1)
    time.sleep(0.05)
    led.value(0)
    time.sleep(0.5)
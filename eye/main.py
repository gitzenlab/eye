import gc
import ota
import time
import machine
import network
import ntptime
import dotmatrix

gc.collect()
gc.enable()

TIMEZONE_OFFSET_SECONDS = 19800

ota = ota.ota()
led = machine.Pin(2, machine.Pin.OUT)
spi = machine.SPI(2, baudrate=10000000, polarity=1, phase=0, sck=machine.Pin(18), mosi=machine.Pin(23))
cs = machine.Pin(5, machine.Pin.OUT)
display = dotmatrix.dotmatrix(spi, cs, 4)

display.brightness(10)
display.clear()
display.show()

display.text("SONA")
display.show()

time.sleep(2)

display.clear()
display.show()

time.sleep(1)

screen_update_timer_id = 2
ntp_update_timer_id = 3

screen_update_due = False
ntp_update_due = False
time_valid = False

screen_timer = machine.Timer(screen_update_timer_id)
ntp_timer = machine.Timer(ntp_update_timer_id)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

if wlan.isconnected():
    try:
        ntptime.settime()
        time_valid = True
    except OSError as e:
        pass

def ntp_update(timer):
    global ntp_update_due
    ntp_update_due = True

def screen_update(timer):
    global screen_update_due
    screen_update_due = True
    
screen_timer.init(mode=machine.Timer.PERIODIC, period=500, callback=screen_update)
ntp_timer.init(mode=machine.Timer.PERIODIC, period=900000, callback=ntp_update)

def get_local_time(offset_seconds):
    utc_seconds = time.time()
    local_seconds = utc_seconds + offset_seconds
    local_time_tuple = time.localtime(local_seconds)
    return local_time_tuple

while True:
    if screen_update_due:
        if time_valid:
            led.value(not led.value())
            current_local_time = get_local_time(TIMEZONE_OFFSET_SECONDS)
            #print("Local time: {0}/{1}/{2} {3}:{4}:{5}".format(*current_local_time))
            current_time = "{:02d}:{:02d}:{:02d}".format(current_local_time[3], current_local_time[4], current_local_time[5])
            
            display.clear()
            display.matrix(str(current_time[0]), x_offset=1)
            display.matrix(str(current_time[1]), x_offset=8)
            if not led.value():
                display.matrix(str(current_time[2]), x_offset=15)
            display.matrix(str(current_time[3]), x_offset=18)
            display.matrix(str(current_time[4]), x_offset=25)
            display.show()
        else:
            display.clear()
            display.text("::::")
            display.show()
            if wlan.isconnected():
                try:
                    ntptime.settime()
                    display.clear()
                    display.fill(1)
                    display.show()
                    time_valid = True
                except OSError as e:
                    display.clear()
                    display.fill(0)
                    display.show()
            else:
                try:
                    ota.wificonnect()
                    if wlan.isconnected():
                        try:
                            ntptime.settime()
                            display.clear()
                            display.fill(1)
                            display.show()
                            time_valid = True
                        except OSError as e:
                            display.clear()
                            display.fill(0)
                            display.show()
                except OSError as e:
                    pass
        screen_update_due = False
        
    if ntp_update_due:
        if wlan.isconnected():
            try:
                ntptime.settime()
                display.clear()
                display.fill(1)
                display.show()
                time_valid = True
            except OSError as e:
                display.clear()
                display.fill(0)
                display.show()
        else:
            try:
                ota.wificonnect()
                if wlan.isconnected():
                    try:
                        ntptime.settime()
                        display.clear()
                        display.fill(1)
                        display.show()
                        time_valid = True
                    except OSError as e:
                        display.clear()
                        display.fill(0)
                        display.show()
            except OSError as e:
                pass
        ntp_update_due = False

    time.sleep(0.05)

"""

DOTMATRIX DIGITAL CLOCK

NETWORK TIME SYNCHRONISED

DARKNESS SENSITIVE DISPLAY

8x32 MAX7219 DOTMATRIX SPACE


------------------------------
DOTMATRIX MODULE CONNECTION:
------------------------------
DOTMATRIX          ESP32

VCC                5V

GND                GND

DIN                D23

CS                 D5

CLK                D18
------------------------------


------------------------------
NEOPIXEL RING CONNECTION:
------------------------------
NEOPIXEL           ESP32

VCC                5V

GND                GND

DIN                D33
------------------------------


------------------------------
I2C MULTI-SENSOR CONNECTION:
------------------------------
MULTI-SENSOR       ESP32

VCC                3V3

GND                GND

SDA                D21

SCL                D22
------------------------------


------------------------------
LIGHT SENSOR CONNECTION:
------------------------------
LIGHT SENSOR       ESP32

VCC                3V3

GND                GND

DOUT               D15
------------------------------


------------------------------
ONEWIRE TEMP SENSOR CONNECTION:
------------------------------
TEMP SENSOR        ESP32

VCC                3V3

GND                GND

DATA               D4
------------------------------


"""


import gc
import ota
import time
import ujson
import sensor
import machine
import network
import ntptime
import onewire
import ds18x20
import neopixel
import dotmatrix
import umqtt.robust


################# SETTINGS #################

DOTMATRIX_BRIGHTNESS_LEVEL_DARK = 0
DOTMATRIX_BRIGHTNESS_LEVEL_LIGHT = 15
DOTMATRIX_CHIPSELECT_PIN = 5
DOTMATRIX_NUMBER_OF_MODULES = 4
DOTMATRIX_STARTUP_BLANK_DURATION = 1
DOTMATRIX_STARTUP_MESSAGE = "SONA"                          ### check and customise ###
DOTMATRIX_STARTUP_MESSAGE_DURATION = 2
I2C_BUS_CLK_FREQUENCY = 400000
I2C_BUS_FOR_SENSOR = 0
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
LIGHT_SENSOR_DOUT_PIN = 15
LOOP_SLEEP_DELAY = 0.05
NEOPIXEL_DATA_PIN = 33
NEOPIXEL_PIXEL_COUNT = 16                                    ### check and customise ###
NTP_TIME_SYNC_INTERVAL_MS = 900000
NTP_UPDATE_HARDWARE_TIMER_ID = 3
ONBOARD_LED_BLINK_PIN = 2
ONEWIRE_DATA_PIN = 4
ONEWIRE_TEMP_SENSOR_RESOLUTION = 12
SCREEN_UPDATE_HARDWARE_TIMER_ID = 2
SCREEN_UPDATE_INTERVAL_MS = 500
SENSOR_UPDATE_HARDWARE_TIMER_ID = 1
SENSOR_UPDATE_INTERVAL_MS = 120000
SPI_BUS_CLK_PIN = 18
SPI_BUS_COMMUNICATION_BAUDRATE = 10000000
SPI_BUS_DOUT_PIN = 23
SPI_BUS_FOR_DOTMATRIX_DISPLAY = 2
TIMEZONE_OFFSET_SECONDS = 19800
UBIDOTS_BROKER = "industrial.api.ubidots.com"
UBIDOTS_CLIENT = "eye"                                       ### check and customise ###
UBIDOTS_MQTT_PORT = 1883
UBIDOTS_MQTT_TOPIC = b"/v1.6/devices/eye"                    ### check and customise ###
UBIDOTS_TOKEN = "BBUS-VtQXRj7OuzPJeROhlvMyxrblwDTe4g"        ### check and customise ###
WDT_TIMEOUT_MS = 30000

################# SETTINGS #################


gc.collect()
gc.enable()

ota = ota.ota()
led = machine.Pin(ONBOARD_LED_BLINK_PIN, machine.Pin.OUT)
spi = machine.SPI(SPI_BUS_FOR_DOTMATRIX_DISPLAY, baudrate=SPI_BUS_COMMUNICATION_BAUDRATE, polarity=1, phase=0, sck=machine.Pin(SPI_BUS_CLK_PIN), mosi=machine.Pin(SPI_BUS_DOUT_PIN))
cs = machine.Pin(DOTMATRIX_CHIPSELECT_PIN, machine.Pin.OUT)
display = dotmatrix.dotmatrix(spi, cs, DOTMATRIX_NUMBER_OF_MODULES)
neo = neopixel.NeoPixel(machine.Pin(NEOPIXEL_DATA_PIN), NEOPIXEL_PIXEL_COUNT)
dark = machine.Pin(LIGHT_SENSOR_DOUT_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
ds = ds18x20.DS18X20(onewire.OneWire(machine.Pin(ONEWIRE_DATA_PIN)))
i2c = machine.I2C(I2C_BUS_FOR_SENSOR, scl=machine.Pin(I2C_SCL_PIN), sda=machine.Pin(I2C_SDA_PIN), freq=I2C_BUS_CLK_FREQUENCY)
ubidots = umqtt.robust.MQTTClient(UBIDOTS_CLIENT, UBIDOTS_BROKER, UBIDOTS_MQTT_PORT, user = UBIDOTS_TOKEN, password = UBIDOTS_TOKEN)
wdt = machine.WDT(timeout=WDT_TIMEOUT_MS)

screen_update_due = False
sensor_update_due = False
ntp_update_due = False
cloud_update_due = False
system_time_synchronised = False
multi_sensor_active = False
onewire_sensor_active = False
onewire_wait_due = False
onewire_read_due = False
ubidots_connected = False

color_pointer = 0
aht20_temperature = 0
aht20_relative_humidity = 0
bmp280_temperature = 0
bmp280_pressure = 0
ds18b20_temperature = 0

screen_timer = machine.Timer(SCREEN_UPDATE_HARDWARE_TIMER_ID)
sensor_timer = machine.Timer(SENSOR_UPDATE_HARDWARE_TIMER_ID)
ntp_timer = machine.Timer(NTP_UPDATE_HARDWARE_TIMER_ID)
display.brightness(DOTMATRIX_BRIGHTNESS_LEVEL_DARK)

try:
    aht20 = sensor.aht20(i2c)
    bmp280 = sensor.bmp280(i2c)
    multi_sensor_active = True
except OSError as e:
    multi_sensor_active = False    

ap_if = network.WLAN(network.AP_IF)
if ap_if.active():
    ap_if.active(False)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

try:
    roms = ds.scan()
    ds.resolution(roms[0], ONEWIRE_TEMP_SENSOR_RESOLUTION)
    onewire_sensor_active = True
except Exception as e:
    onewire_sensor_active = False

display.clear()
display.show()
display.text(DOTMATRIX_STARTUP_MESSAGE)
display.show()
time.sleep(DOTMATRIX_STARTUP_MESSAGE_DURATION)
display.clear()
display.show()
time.sleep(DOTMATRIX_STARTUP_BLANK_DURATION)

if wlan.isconnected():
    try:
        ntptime.settime()
        system_time_synchronised = True
    except OSError as e:
        pass

def get_local_time(offset_seconds):
    utc_seconds = time.time()
    local_seconds = utc_seconds + offset_seconds
    local_time_tuple = time.localtime(local_seconds)
    return local_time_tuple

def initiate_onewire_read():
    global ds18b20_temperature
    
    if onewire_sensor_active:
        try:
            ds.convert_temp()
        except Exception as e:
            onewire_sensor_active = False
            ds18b20_temperature = 0
    else:
        ds18b20_temperature = 0

def onewire_read_data():
    global ds18b20_temperature
    
    if onewire_sensor_active:
        try:
            ds18b20_temperature = round(ds.read_temp(0),2)
        except Exception as e:
            onewire_sensor_active = False
            ds18b20_temperature = 0
    else:
        ds18b20_temperature = 0

def update_cloud():
    global ubidots_connected
    
    global aht20_temperature
    global aht20_relative_humidity
    global bmp280_temperature
    global bmp280_pressure
    
    if not ubidots_connected:
        if wlan.isconnected():
            try:
                ubidots.connect()
                ubidots_connected = True
            except Exception as e:
                ubidots_connected = False
        else:
            ubidots_connected = False
            
    if ubidots_connected:
        if bmp280_pressure > 0 or aht20_relative_humidity > 0 or ds18b20_temperature > 0:
            try:
                sensor_data = {
                    "air_temperature": aht20_temperature,
                    "air_pressure": bmp280_pressure,
                    "relative_humidity": aht20_relative_humidity,
                    "water_temperature": ds18b20_temperature
                }
                json_payload = ujson.dumps(sensor_data)
                ubidots.publish(UBIDOTS_MQTT_TOPIC, json_payload.encode('utf-8'))
            except Exception as e:
                ubidots_connected = False
            
    aht20_temperature = 0
    aht20_relative_humidity = 0
    bmp280_temperature = 0
    bmp280_pressure = 0
    ds18b20_temperature = 0

def multi_sensor():
    global multi_sensor_active
    
    global aht20_temperature
    global aht20_relative_humidity
    global bmp280_temperature
    global bmp280_pressure
    
    global aht20
    global bmp280
    
    if multi_sensor_active:
        try:
            aht20_temperature = round(aht20.temperature,2)
            aht20_relative_humidity = round(aht20.relative_humidity,2)
            bmp280_temperature = round(bmp280.temperature,2)
            bmp280_pressure = round(bmp280.pressure/100,2)
        except OSError as e:
            multi_sensor_active = False
    else:
        try:
            devices = i2c.scan()
            if len(devices) == 0:
                multi_sensor_active = False
            else:
                #print(f"Found {len(devices)} I2C devices:\n")
                #for device in devices:
                    #print(f"Decimal address: {device} | Hexadecimal address: {hex(device)}") 
                try:
                    aht20 = sensor.aht20(i2c)
                    bmp280 = sensor.bmp280(i2c)
                    multi_sensor_active = True
                except OSError as e:
                    multi_sensor_active = False
        except OSError as e:
            multi_sensor_active = False  

def rainbow():
    global color_pointer
    
    numpixel = neo.n
    color_pointer = color_pointer - numpixel + 1
    
    if color_pointer < 0:
        color_pointer = color_pointer + 1 + 255
    for i in range(numpixel):
        if color_pointer < 85:
            pixel_color = color_pointer & 255
            neo[i] = (pixel_color * 3, 255 - pixel_color * 3, 0)
        elif color_pointer < 170:
            pixel_color = color_pointer & 255 - 85
            neo[i] = (255 - pixel_color * 3, 0, pixel_color * 3)
        else:
            pixel_color = color_pointer & 255 - 170
            neo[i] = (0, pixel_color * 3, 255 - pixel_color * 3)
        color_pointer = color_pointer + 1
        if color_pointer > 255:
            color_pointer = 0
    neo.write()

def ntp_update(timer):
    global ntp_update_due
    ntp_update_due = True

def sensor_update(timer):
    global sensor_update_due
    sensor_update_due = True

def screen_update(timer):
    global screen_update_due
    screen_update_due = True

screen_timer.init(mode=machine.Timer.PERIODIC, period=SCREEN_UPDATE_INTERVAL_MS, callback=screen_update)
sensor_timer.init(mode=machine.Timer.PERIODIC, period=SENSOR_UPDATE_INTERVAL_MS, callback=sensor_update)
ntp_timer.init(mode=machine.Timer.PERIODIC, period=NTP_TIME_SYNC_INTERVAL_MS, callback=ntp_update)

while True:
    if screen_update_due:
        if system_time_synchronised:
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
            
            if sensor_update_due:
                multi_sensor()
                initiate_onewire_read()
                sensor_update_due = False
                onewire_wait_due = True
                rainbow()
            elif onewire_wait_due:
                onewire_wait_due = False
                onewire_read_due = True
                rainbow()
            elif onewire_read_due:
                onewire_read_data()
                onewire_read_due = False
                cloud_update_due = True
                rainbow()
            elif cloud_update_due:                
                update_cloud()
                cloud_update_due = False
                rainbow()
            else:
                rainbow()
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
                    system_time_synchronised = True
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
                            system_time_synchronised = True
                        except OSError as e:
                            display.clear()
                            display.fill(0)
                            display.show()
                except OSError as e:
                    pass
                    
        wdt.feed()
        screen_update_due = False
        
        if dark.value():
            display.brightness(DOTMATRIX_BRIGHTNESS_LEVEL_DARK)
        else:
            display.brightness(DOTMATRIX_BRIGHTNESS_LEVEL_LIGHT)
        
    if ntp_update_due:
        if wlan.isconnected():
            try:
                ntptime.settime()
                display.clear()
                display.fill(1)
                display.show()
                system_time_synchronised = True
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
                        system_time_synchronised = True
                    except OSError as e:
                        display.clear()
                        display.fill(0)
                        display.show()
            except OSError as e:
                pass
        ntp_update_due = False
        
    time.sleep(LOOP_SLEEP_DELAY)

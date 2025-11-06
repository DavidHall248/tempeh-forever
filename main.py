import time
import network
import framebuf
import machine
import math
import max31865
from machine import I2C, ADC, Pin, WDT
from umqtt.simple import MQTTClient
from sh1106 import SH1106_I2C

wifi_ssid = <WIFI_NETWORK>
wifi_password = <WIFI_PASSWORD>

#Setup OLED Screen
i2c = I2C(0, scl=Pin(9), sda=Pin(8))            
oled = SH1106_I2C(128, 64, i2c)
#Setup temp sensor
spi = machine.SPI(0, baudrate=400000, polarity=0, phase=1)
cs = machine.Pin(17)
sensor = max31865.MAX31865(spi, cs)

tempUp = Pin(12, Pin.IN)
tempUp_msSinceLast = 0

tempDown = Pin(13, Pin.IN)
tempDown_msSinceLast = 0

toggle_mqtt = Pin(11, Pin.IN)
toggle_mqtt_msSinceLast = 0

screen_msSinceLast = 0
mqtt_msSinceLast = 0
temp_msSinceLast = 0
heatRelay_msSinceLast = 0
fanRelay_msSinceLast = 0

mqtt_status = True
wifi_status = False
heatRelayPin = Pin(22, Pin.OUT)
fanRelayPin = Pin(28, Pin.OUT)
heatRelayStatus = False
fanRelayStatus = False

targetTemp = 90

#Connect to WIFI
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(wifi_ssid, wifi_password)

while(wlan.isconnected() == False):
    time.sleep(1)
    
# Initialize our MQTTClient and connect to the MQTT server
mqtt_client = MQTTClient(
        client_id="pico1",
        server="192.168.0.26",
#        user=mqtt_username,
#        password=mqtt_password
        )

def mqtt_subscription_callback(topic, message):
    print (f'Topic {topic} received message {message}')
    oled.fill(0)
    oled.text(message,5,5)
    oled.show()

mqtt_client.set_callback(mqtt_subscription_callback)
mqtt_client.connect()

def refreshScreen():
    oled.fill(0)
    oled.text("Temp: "   + str(round(T,1)), 5, 5)
    oled.text("Target: " + str(round(targetTemp,1)), 5, 15)
    oled.text("Heat: "   + str("On" if heatRelayStatus else "Off"), 5, 25)
    oled.text("Fan: "    + str("On" if fanRelayStatus else "Off"), 5, 35)
    oled.text("MQTT: "   + str("On" if mqtt_status else "Off"), 5, 45)
    oled.text("Wifi: "   + str("On" if wlan.isconnected() else "Off"), 5, 55)
    oled.show()

last_ms = time.ticks_ms()

wdt = WDT(timeout=8000)
while(True):
    
    if(wlan.isconnected() == False):
        #Reconnect to WIFI if signal is lost
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(wifi_ssid, wifi_password)
        while(wlan.isconnected() == False):
            time.sleep(1)
    
    elapsed_ms = time.ticks_diff(time.ticks_ms(),last_ms)
    last_ms = time.ticks_ms()
    
    tempUp_msSinceLast      = max(tempUp_msSinceLast      - elapsed_ms, 0)
    tempDown_msSinceLast    = max(tempDown_msSinceLast    - elapsed_ms, 0)
    toggle_mqtt_msSinceLast = max(toggle_mqtt_msSinceLast - elapsed_ms, 0)
    heatRelay_msSinceLast   = max(heatRelay_msSinceLast   - elapsed_ms, 0)
    fanRelay_msSinceLast    = max(fanRelay_msSinceLast    - elapsed_ms, 0)
    screen_msSinceLast      = max(screen_msSinceLast      - elapsed_ms, 0)
    mqtt_msSinceLast        = max(mqtt_msSinceLast        - elapsed_ms, 0)
    temp_msSinceLast        = max(temp_msSinceLast        - elapsed_ms, 0)
    #print(elapsed_ms)
    
    if(temp_msSinceLast <= 0):
        temp_msSinceLast = 1000
        T,R = sensor.read_all()
        T = T * 9 / 5 + 32 #Convert to F
    
    #Process button presses while avoiding switch bounces
    if tempUp.value():
        if tempUp_msSinceLast <= 0:
            targetTemp = targetTemp + 1
        tempUp_msSinceLast = 100
        
    if tempDown.value():
        if tempDown_msSinceLast <= 0:
            targetTemp = targetTemp - 1
        tempDown_msSinceLast = 100
        
    if toggle_mqtt.value():
        if toggle_mqtt_msSinceLast <= 0:
            mqtt_status = False if mqtt_status else True
        toggle_mqtt_msSinceLast = 100
    
    #Send MQTT Updates
    try:
        #If temp is over target and relay is on, turn it off. Do not check for time limit
        if targetTemp <= T and heatRelayStatus == True:
            heatRelayPin.value(0)
            heatRelayStatus = False
            heatRelay_msSinceLast = 30000
            mqtt_client.publish("tempeh/events/heat", str(0))
            print("tempeh/events/heat: " + str(0))
        
        #If temp is under and relay is off, turn it on, but check for time limit
        if heatRelay_msSinceLast <= 0:
            if targetTemp > T and heatRelayStatus == False:
                heatRelayPin.value(1)
                heatRelayStatus = True
                heatRelay_msSinceLast = 30000
                mqtt_client.publish("tempeh/events/heat", str(1))
                print("tempeh/events/heat: " + str(1))
              
        #If temp is more than 5 degrees over target, turn on fan
        if targetTemp + 5 < T and fanRelayStatus == False:
            fanRelayPin.value(1)
            fanRelayStatus = True
            mqtt_client.publish("tempeh/events/fan", str(1))
            print("tempeh/events/heat: " + str(1))
              
        #If temp is under target and fan is on, turn it off
        if targetTemp >= T and fanRelayStatus == True:
            fanRelayPin.value(0)
            fanRelayStatus = False
            mqtt_client.publish("tempeh/events/fan", str(0))
            print("tempeh/events/heat: " + str(0))
        
        #Check mqtt timer and send temp update
        if(mqtt_status and mqtt_msSinceLast == 0):
            msg = str(round(T,2))
            mqtt_client.publish("tempeh/measurements", msg)
            mqtt_msSinceLast = 60000
            print("tempeh/measurements: " + msg)
            
    except Exception as e:
        print("MQTT Error:", e)
    
    
    #Update LED screen
    try:
        refreshScreen()
    except Exception as e:
        print("Screen Error:", e)

    time.sleep(.1)
    wdt.feed()


 

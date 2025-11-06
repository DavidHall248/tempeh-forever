import sys
import os
import paho.mqtt.client as mqtt
import json
import psycopg2
from psycopg2 import sql
from datetime import datetime

#E-Ink Library
picdir = "/home/admin/e-Paper/RaspberryPi_JetsonNano/python/pic"
libdir = "/home/admin/e-Paper/RaspberryPi_JetsonNano/python/lib"
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd3in52
import time
from PIL import Image,ImageDraw,ImageFont
import traceback

logging.basicConfig(level=logging.DEBUG)

try:
    epd = epd3in52.EPD()
    epd.init()
    epd.display_NUM(epd.WHITE)
    epd.lut_GC()
    epd.refresh()

    epd.send_command(0x50)
    epd.send_data(0x17)
    epd.Clear()
    time.sleep(1)
    
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
    font36 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 36)
    
    screenOffset = 110
    
    Limage = Image.new('1', (epd.width, epd.height), 255)  # 255: clear the frame
    draw = ImageDraw.Draw(Limage)
    draw.text((2, 0 + screenOffset), 'Booting Up...', font = font18, fill = 0)
    epd.display(epd.getbuffer(Limage))
    epd.lut_GC()
    epd.refresh()
        
except IOError as e:
    logging.info(e)


conn_str = "postgresql://<CONNECTION STRING HERE>"
lastMessageTime = datetime.min
messageTimeList = []

def addAndCleanTimes():
    for i in range(len(messageTimeList))[::-1]:
        print(messageTimeList[i])
        if (datetime.now() - messageTimeList[i]).total_seconds() > 15 * 60:
            del messageTimeList[i]

def on_connect(client, userdata, flags, rc):
    print("MQTT Connected: ", rc)
    client.subscribe("tempeh/measurements")
    client.subscribe("tempeh/events/#")

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    query = "SELECT 1"
    data = ("error", -999)
    try:
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        if msg.topic == "tempeh/events/heat":
            data = ("heat_relay", int(payload))
            query = "INSERT INTO events (category, value) VALUES (%s, %s);"
        elif msg.topic == "tempeh/events/fan":
            data = ("fan_relay", int(payload))
            query = "INSERT INTO events (category, value) VALUES (%s, %s);" 
        elif msg.topic == "tempeh/measurements":
            data = ("temperature", float(payload))
            query = "INSERT INTO measurements (category, value) VALUES (%s, %s);"
    
        cursor.execute(query, data)
        conn.commit()
        cursor.close()
        conn.close()
    
    except Exception as e:
        print(f"Connection Error: {e}")

    global lastMessageTime
    messageTimeList.append(datetime.now())
    if (datetime.now() - lastMessageTime).total_seconds() >= 60:
        lastMessageTime = datetime.now()
        addAndCleanTimes()
        # Drawing on the Vertical image
        Limage = Image.new('1', (epd.width, epd.height), 255)  # 255: clear the frame
        draw = ImageDraw.Draw(Limage)
        draw.text((2, 0 + screenOffset), 'Last Message:', font = font18, fill = 0)
        draw.text((2, 20 + screenOffset), lastMessageTime.strftime("%I:%M %p"), font = font36, fill = 0)
        draw.text((2, 60 + screenOffset), 'Messages in past 15 minutes:', font = font18, fill = 0)
        draw.text((2, 80 + screenOffset), str(len(messageTimeList)), font = font36, fill = 0)
        epd.display(epd.getbuffer(Limage))
        epd.lut_GC()
        epd.refresh()

try:
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
except Exception as e:
    print(f"Connection Error: {e}")


client = mqtt.Client("DataProcessor")
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost")

client.loop_forever()
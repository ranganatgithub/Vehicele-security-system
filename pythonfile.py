import time
from pyfingerprint.pyfingerprint import PyFingerprint
import RPi.GPIO as GPIO
import serial
import board
import busio
import adafruit_adxl34x

# GPIO setup
relay = 40
GPIO.setmode(GPIO.BOARD)
GPIO.setup(relay, GPIO.OUT)
GPIO.output(relay, 1)

# Initialize fingerprint sensor
try:
    f = PyFingerprint('/dev/ttyUSB0', 57600, 0xFFFFFFFF, 0x00000000)
    if not f.verifyPassword():
        raise ValueError("The given fingerprint sensor password is wrong!")
except Exception as e:
    print('Exception message: ' + str(e))
    exit(1)

# Fingerprint Enrollment
def enrollFinger():
    print('Place your finger to enroll ... ')
    while not f.readImage():
        pass

    f.convertImage(0x01)
    result = f.searchTemplate()
    positionNumber = result[0]

    if positionNumber >= 0:
        print("Template already exists at position " + str(positionNumber))
        return

    print('Remove finger ... ')
    time.sleep(2)
    print('Waiting for the same finger again ... ')

    while not f.readImage():
        pass

    f.convertImage(0x02)
    
    if f.compareCharacteristics() == 0:
        print("Fingers do not match")
        return

    f.createTemplate()
    positionNumber = f.storeTemplate()
    
    print('Finger enrolled successfully!')
    print('Stored at Position: ' + str(positionNumber))
    time.sleep(2)

# Fingerprint Search
def searchFinger():
    try:
        print('Waiting for finger ... ')
        while not f.readImage():
            pass

        f.convertImage(0x01)
        result = f.searchTemplate()
        positionNumber = result[0]

        if positionNumber == -1:
            print('No match found!')
            time.sleep(2)
            return
        else:
            print('Found template at position ' + str(positionNumber))
            GPIO.output(relay, 0)
            time.sleep(1)
            GPIO.output(relay, 1)

    except Exception as e:
        print('Operation failed!')
        print('Exception message: ' + str(e))
        exit(1)

while True:
    searchFinger()

# ADXL SENSOR SETUP
i2c = busio.I2C(board.SCL, board.SDA)
accelerometer = adafruit_adxl34x.ADXL345(i2c)
accelerometer.enable_freefall_detection(threshold=10, time=25)
accelerometer.enable_motion_detection(threshold=18)
accelerometer.enable_tap_detection(tap_count=1, threshold=20, duration=50, latency=20, window=255)

# GPS and GSM Setup
gps = serial.Serial("/dev/ttyS0", baudrate=9600)
link1 = 'http://maps.google.com/maps?q=loc:'
pin = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Function to Send SMS
def gsm_send(msg, num):
    gps.write(b'AT\r')
    time.sleep(1)
    gps.write(b'AT+CMGF=1\r')
    time.sleep(1)
    gps.write(b'AT+CMGS="' + num.encode() + b'"\r')
    time.sleep(1)
    gps.write(msg.encode())
    gps.write(b'\x1A')
    time.sleep(3)
    print("Message sent")

# GPS Tracking Function
def gps_on():
    while True:
        line = gps.readline()
        data = line.split(b",")
        if data[0] == b"$GNRMC" and data[2] == b"A":
            latgps = float(data[3])
            latdeg = int(latgps / 100)
            latmin = latgps - latdeg * 100
            lat = latdeg + (latmin / 60)

            longps = float(data[5])
            londeg = int(longps / 100)
            lonmin = longps - londeg * 100
            lon = londeg + (lonmin / 60)

            link = f"{link1}{lat},{lon}"
            print(link)
            msg = f"Accident happened! Please visit the location: {link}"
            gsm_send(msg, '7676578382')
            break

# ADXL Sensor Monitoring
while True:
    var = accelerometer.acceleration
    var1 = var[2]
    print("ADXL value =", var1)
    time.sleep(1)

    var2 = GPIO.input(pin)
    print("Wire value =", var2)
    time.sleep(1)

    if var1 <= 5:
        print("Message sent: Accident detected")
        gps_on()
        time.sleep(1)
    else:
        print("No accident detected")

    if var2 == 1:
        print("Wire cut detected! Possible theft.")
        gps_on()
    else:
        print("No wire cut detected")

# ULTRASONIC SENSOR SETUP
GPIO.setmode(GPIO.BOARD)
GPIO_TRIGGER = 37
GPIO_ECHO = 38
relay = 40
led = 35

GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
GPIO.setup(relay, GPIO.OUT)
GPIO.setup(led, GPIO.OUT)

# Distance Measurement
while True:
    GPIO.output(GPIO_TRIGGER, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)

    StartTime = time.time()
    StopTime = time.time()

    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()

    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()

    TimeElapsed = StopTime - StartTime
    distance = (TimeElapsed * 34300) / 2
    var = round(distance)
    print(var)
    time.sleep(1)

    if var <= 10:
        print("Please maintain the distance")
        GPIO.output(relay, 0)
        GPIO.output(led, 0)
    else:
        print("Move slowly")
        GPIO.output(relay, 1)
        GPIO.output(led, 1)

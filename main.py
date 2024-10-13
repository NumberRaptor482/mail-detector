# Import Modules
import time
import machine
import urequests
import ujson
import network
from machine import Pin, PWM

# GPIO Pin Definitions
TRIG_PIN = 3  # GPIO pin for HC-SR04 Trig
ECHO_PIN = 2  # GPIO pin for HC-SR04 Echo

# Distance Alert Threshhold (in cm)
THRESHOLD = 5

# Distance Sensor Pin Configurations
trigger = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

# LED Indicator Setup
indicator = Pin("LED", Pin.OUT)
indicator.off()


# Network Credentials Configuration
def load_credentials(filename):
    
    try:
        with open(filename, "r") as file:
            data = ujson.load(file)
            return data
    
    except OSError:
        print("Error reading secrets.json")
        return None

secrets = load_credentials("credentials.json")


# IoT Device Object
class device:
    def __init__(self, trigger, echo, led, credentials):
        self.trigger = trigger
        self.echo = echo
        self.led = led
        self.ssid = credentials.get("ssid")
        self.password = credentials.get("password")
        self.webhook = credentials.get("webhook")


    def connect(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.ssid, self.password)

        while not wlan.isconnected():
            print("Connecting to WiFi...")
            time.sleep(1)

        print("WiFi connected! IP:", wlan.ifconfig())
    

    def distance(self):
        # Send 10us pulse to trigger the sensor
        self.trigger.low()
        time.sleep_us(2)
        self.trigger.high()
        time.sleep_us(10)
        self.trigger.low()

        # Measure the duration of the pulse
        while self.echo.value() == 0:
            pulse_start = time.ticks_us()

        while self.echo.value() == 1:
            pulse_end = time.ticks_us()

        # Calculate distance in cm
        pulse_duration = time.ticks_diff(pulse_end, pulse_start)
        distance = (pulse_duration * 0.0343) / 2  # Speed of sound is 343 m/s

        return distance
    

    def alert(self, content):
        payload = {
            "content": content
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = urequests.post(
                self.webhook, 
                json=payload, 
                headers=headers
            )
            
            if response.status_code == 204:  # Discord returns 204 No Content on success
                print("alert sent to discord")
            else:
                print(f"failed to send alert, status code: {response.status_code}")
            
            response.close()
        
        except Exception as error:
            print(f"error sending alert: {error}")

    
    def detection(self, threshhold):
        
        if self.distance() < threshhold:
            return True
        
        return False


# Main Loop
def main():

    mailbox = device(
        trigger, 
        echo, 
        indicator, 
        secrets
    )
    
    mailbox.connect()

    while True:

        print(f"measured distance: {mailbox.distance()} cm")

        if mailbox.detection(THRESHOLD):
            mailbox.led.on()
            mailbox.alert("You have mail!")

        else:
            mailbox.led.off()

        time.sleep(0.25)

# Run Main Loop
main()

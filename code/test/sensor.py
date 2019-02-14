import RPi.GPIO as GPIO
import time

# photo sensor on PIN 5
GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.IN)

# LED on PIN 22
GPIO.setup(22, GPIO.OUT)
GPIO.output(22, GPIO.LOW)

try:
    print('Start sensor test - End with Ctrl-C')
    
    while True:
        time.sleep(1)
        if (GPIO.input(5) == GPIO.LOW):
            print('LOW')
            GPIO.output(22, GPIO.LOW)
        else:
            print('HIGH')
            GPIO.output(22, GPIO.HIGH)

except KeyboardInterrupt:
    print('KeyboardInterrupt')
GPIO.cleanup()


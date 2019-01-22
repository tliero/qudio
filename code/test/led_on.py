import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

GPIO.setup(22,GPIO.OUT)
GPIO.output(22,GPIO.HIGH)


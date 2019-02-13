# piplayer4 - Qudio
# http://www.tilman.de/projekte/qudio

import RPi.GPIO as GPIO
import logging
import time
import subprocess
import select  # for polling zbarcam, see http://stackoverflow.com/a/10759061/3761783
from socketIO_client import SocketIO, LoggingNamespace # see https://gist.github.com/ivesdebruycker/4b08bdd5415609ce95e597c1d28e9b9e
from threading import Thread


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s - %(message)s')
logging.info('Initializing')

# Configuration
MUSIC_BASE_DIRECTORY = "mnt/"
SOUND_SCANNING = "mnt/INTERNAL/qudio/sounds/scanning.mp3"
SOUND_SCAN_FAIL = "mnt/INTERNAL/qudio/sounds/fail-05.mp3"
QR_SCANNER_TIMEOUT = 4

# photo sensor on PIN 5
PIN_SENSOR = 5

# LED on PIN 22
PIN_LED = 22

# Buttons on PINs 9, 10 and 11
PIN_PREV = 9
PIN_NEXT = 10
PIN_PLAY = 11


GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_LED, GPIO.OUT)
GPIO.output(PIN_LED, GPIO.LOW)
GPIO.setup(PIN_PREV, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_PLAY, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_NEXT, GPIO.IN, pull_up_down=GPIO.PUD_UP)


is_playing = False # for toggling play/pause (stores the current status from the pushState events)

socketIO = SocketIO('localhost', 3000)


def play(uri, service = 'mpd'):
    socketIO.emit('replaceAndPlay', {'service':service,'uri':uri})

def prev_callback(channel):
    logging.info("PREV")
    socketIO.emit('prev')
    ## TODO implement jump to beginning for first x seconds (or if first track)
    ## TODO implement seek
     
def play_callback(channel):
    global is_playing
    if is_playing:
        logging.info("PAUSE")
        socketIO.emit('pause')
    else:
        logging.info("PLAY")
        socketIO.emit('play')

def next_callback(channel):
    logging.info("NEXT")
    socketIO.emit('next')
    ## TODO implement seek

def on_pushState(*args):
    logging.debug(args[0]['status'])
    global is_playing
    if args[0]['status'] == 'play':
        is_playing = True
    else:
        is_playing = False

def events_thread():
    socketIO.wait()


GPIO.add_event_detect(PIN_PREV, GPIO.FALLING, callback=prev_callback, bouncetime=400)
GPIO.add_event_detect(PIN_PLAY, GPIO.FALLING, callback=play_callback, bouncetime=400)
GPIO.add_event_detect(PIN_NEXT, GPIO.FALLING, callback=next_callback, bouncetime=400)


try:
    socketIO.on('pushState', on_pushState)
    listener_thread = Thread(target=events_thread)
    listener_thread.daemon = True
    listener_thread.start()

    while True:
        logging.info('Wait for photo sensor')
        GPIO.wait_for_edge(PIN_SENSOR, GPIO.FALLING)
        
        logging.info('Photo sensor active, activating light and camera')
        play(SOUND_SCANNING)
        
        # turn LED on
        GPIO.output(PIN_LED, GPIO.HIGH)
        
        # scan QR code
        zbarcam = subprocess.Popen(['zbarcam', '--quiet', '--nodisplay', '--raw', '-Sdisable', '-Sqrcode.enable', '--prescale=320x240', '/dev/video0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        poll_obj = select.poll()
        poll_obj.register(zbarcam.stdout, select.POLLIN)
        
        # wait for scan result (or timeout)
        start_time = time.time()
        poll_result = False
        while ((time.time() - start_time) < QR_SCANNER_TIMEOUT and (not poll_result)):
            poll_result = poll_obj.poll(100)

        if (poll_result):
            qr_code = zbarcam.stdout.readline().rstrip()
            qr_code = qr_code.decode("utf-8") # python3
            logging.info("QR Code: " + qr_code)
            
            if qr_code.startswith("http://") or qr_code.startswith("https://"):
                play(qr_code, 'webradio')
            elif qr_code.startswith("spotify:"):
                play(qr_code, 'spop')
            else:
                # create full path
                if (qr_code.startswith("/")):
                    qr_code = qr_code[1:]
                full_path = MUSIC_BASE_DIRECTORY + qr_code
                logging.debug("full_path: " + full_path)
                play(full_path)
            
        else:
            logging.warning('Timeout on zbarcam')
            play(SOUND_SCAN_FAIL)
            
        zbarcam.terminate()
        GPIO.output(PIN_LED, GPIO.LOW)

        # wait until sensor is not blocked anymore
        if (GPIO.input(PIN_SENSOR) == GPIO.LOW):
            GPIO.wait_for_edge(PIN_SENSOR, GPIO.RISING)
            time.sleep(1)

        
# Exit when Ctrl-C is pressed
except KeyboardInterrupt:
    logging.info('Shutdown')
    
finally:
    logging.info('Reset GPIO configuration and close')
    GPIO.cleanup()

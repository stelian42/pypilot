#!/usr/bin/env python
#
#   Copyright (C) 2019 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import os, time

raspberrypi = False
orangepi = False

try:
    with open('/sys/firmware/devicetree/base/model', 'r') as m:
        if 'raspberry pi' in m.read().lower():
            while True:
                try:
                    f = open('/dev/gpiomem', 'w')
                    f.close()
                    break
                except Exception as e:
                    print('waiting for gpiomem...', e)
                time.sleep(1)
            import RPi.GPIO as GPIO
            print('have gpio for raspberry pi')
            raspberrypi = True
except Exception:
    pass



if not raspberrypi:
    try:
        import OPi.GPIO as GPIO
        orangepi = True
        print('have gpio for orange pi')
    except:
        print('No gpio available')
        GPIO = None

class gpio(object):
    def __init__(self):
        self.keystate = {}
        self.events = []

        if orangepi:
            self.pins = [11, 16, 13, 15, 12]
        else:
            self.pins = [17, 23, 27, 22, 18, 5, 6, 26]

        for pin in self.pins:
            self.keystate[pin] = 0

        if not GPIO:
            return
        
        if orangepi:
            for pin in self.pins:
                cmd = 'gpio -1 mode ' + str(pin) + ' up'
                os.system(cmd)
            GPIO.setmode(GPIO.BOARD)
        else:
            GPIO.setmode(GPIO.BCM)

        for pin in self.pins:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                pass
            except RuntimeError:
                print('failed to open /dev/gpiomem, no permission')
                # if failed, attempt to give current user privilege if no sudo pw
                user = os.getenv('USER')
                os.system('sudo chown ' + user + ' /dev/gpiomem')
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    
            def cbr(pin):
                value = GPIO.input(pin)
                time.sleep(.02)  # workaround buggy gpio
                self.evalkey(pin, value)

            while True:
                try:
                    GPIO.add_event_detect(pin, GPIO.BOTH, callback=cbr, bouncetime=50)
                    break
                except Exception as e:
                    print('WARNING', e)

                if not raspberrypi:
                    break
                print('retrying to setup gpio with edge detect...')
                time.sleep(1)

    def poll(self):
        for pin in self.pins:
            value = True

            if False:
                f = open('/sys/class/gpio/gpio%d/value' % pin)
                a = f.readline()
                value = bool(int(a))
            else:
                if GPIO:
                    value = GPIO.input(pin)

            self.evalkey(pin, value)
        events = self.events
        self.events = []
        return events

    def evalkey(self, pin, value):
        if value:
            if self.keystate[pin]:
                self.keystate[pin] = 0
            else:
                return
        else:
            self.keystate[pin] += 1

        self.events.append(('gpio%d'%pin, self.keystate[pin]))

def main():
    gp = gpio()
    while True:
        events = gp.poll()
        if events:
            print('events', events)
        time.sleep(.1)
            
if __name__ == '__main__':
    main() 

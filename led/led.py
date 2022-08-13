#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# @file         led.py
# @brief        LED Class
# @author       KeitetsuWorks
# @date         2018/08/29
# @copyright    Copyright (c) 2018 Keitetsu
# @par          License
# This software is released under the MIT License.
#
"""LED module

Todo:
    RPi.GPIO library is required.

        $ pip install RPi.GPIO
"""

import RPi.GPIO as GPIO
from enum import Enum
import time


class LEDState(Enum):
    """LED state class
    """
    OFF = 0
    ON = 1


# GPIOのピンアサイン
# https://www.raspberrypi-spy.co.uk/2012/06/simple-guide-to-the-rpi-gpio-header-and-pins/
# GPIO.BCMについて
# https://raspberrypi.stackexchange.com/questions/12966/what-is-the-difference-between-board-and-bcm-for-gpio-pin-numbering
class LED(object):
    """LED control class
    """

    def __init__(self, pin, off_state=1, default_off=True):
        """Constructor

        Args:
            pin (int): GPIO Pin number where LED is connected.
            off_state (int): Output value when LED is OFF. 0 or 1.
            default_off (bool): True if the default LED state is OFF.
        """
        self.pin = pin
        # 既定ではLEDは負論理制御
        # Low(0V)出力: 点灯, High(3.3V)出力: 消灯
        if off_state == 1:
            self._on = GPIO.LOW
            self._off = GPIO.HIGH
        else:
            self._on = GPIO.HIGH
            self._off = GPIO.LOW
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        if default_off:
            self.off()
        else:
            self.on()

        return

    def cleanup(self):
        """End LED control

        End control of LED control and release GPIO pin.
        """
        GPIO.cleanup(self.pin)

        return

    def on(self):
        """Turn on the LED
        """
        GPIO.output(self.pin, self._on)
        self.state = LEDState.ON

    def off(self):
        """Turn off the LED
        """
        GPIO.output(self.pin, self._off)
        self.state = LEDState.OFF


if __name__ == "__main__":
    # LEDのピンアサインDict
    led_conf = {
        'red': {
            'pin': 22,
            'off_state': 0,
            'default_off': True
        },
        'yellow': {
            'pin': 27,
            'off_state': 0,
            'default_off': True
        },
        'green': {
            'pin': 17,
            'off_state': 0,
            'default_off': True
        }
    }
    # LEDのオブジェクトDict
    leds = {
    }

    # LEDの初期化
    for led_name in led_conf:
        # LEDのピンアサインDictを順次読出し、
        # オブジェクトを作成する
        # オブジェクトをDictに追加する
        print("[INFO] create LED object: %s" % (led_name))
        led = LED(led_conf[led_name]['pin'],
                  off_state=led_conf[led_name]['off_state'],
                  default_off=led_conf[led_name]['default_off'])
        leds[led_name] = led

    # 順次点滅を3回繰返す
    for count in range(0, 3):
        for led_name in leds:
            print("[INFO] on LED: %s" % (led_name))
            leds[led_name].on()
            time.sleep(1.0)
            print("[INFO] off LED: %s" % (led_name))
            leds[led_name].off()
            time.sleep(1.0)

    # LEDの解放
    for led_name in leds:
        print("[INFO] clean up LED: %s" % (led_name))
        leds[led_name].cleanup()

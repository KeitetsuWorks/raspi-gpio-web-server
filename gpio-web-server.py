#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# @file         gpio-web-server.py
# @brief        CGI Script to Control LEDs
# @author       KeitetsuWorks
# @date         2021/04/11
# @copyright    Copyright (c) 2021 Keitetsu
# @par          License
# This software is released under the MIT License.
#
"""CGI Script to Control LEDs"""

import argparse
import cgi
import cgitb
import codecs
import datetime
from http import HTTPStatus
import http.server
import queue
import threading

from led.led import LED
from led.led import LEDState


led_ctrl_req_queue = queue.Queue()

led_ctrl_thread_stop = False


class Handler(http.server.CGIHTTPRequestHandler):
    """Customized CGIHTTPRequestHandler
    """

    def do_GET(self):
        """Customized do_GET method

        Customized do_GET method to ignore requests to favicon.
        """
        if self.path.endswith("favicon.ico"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/x-icon")
            self.send_header("Content-Length", 0)
            self.end_headers()
            return

        return super().do_GET()

    def do_POST(self):
        """Customized do_POST method

        Customized do_POST method to provide LED control API.
        """
        if self.path == "/api/led":
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                    environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers["Content-Type"]})
            global led_ctrl_req_queue
            led_ctrl_req_queue.put(form)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = codecs.open("./index.html", "r", "utf-8")
            self.wfile.write(bytes(html.read(), "utf-8"))

            return

        return super().do_POST()


class StoppableThreadingHTTPServer(http.server.ThreadingHTTPServer):
    """ThreadingHTTPServer that can be stopped by KeyboardInterrupt
    """

    def run(self):
        """Run the server
        """
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server_close()


class LEDCtrlThread(threading.Thread):
    """LED control thread class
    """

    def __init__(self, leds):
        """Constructor

        Args:
            leds (dict): LED objects dictionary
        """
        super().__init__()
        self._leds = leds
        self._leds_settings = {}
        dt_now = datetime.datetime.now()
        for led_name in leds:
            self._leds_settings[led_name] = {}
            self._leds_settings[led_name]["last-time"] = dt_now
            self._leds_settings[led_name]["blink"] = False
            self._leds_settings[led_name]["delay-on"] = 500
            self._leds_settings[led_name]["delay-off"] = 500

    def run(self):
        """Run the LED control thread

        Process LED control requests stored in ``led_ctrl_req_queue``.
        When the LED reaches the blinking timing, the state of the LED is toggled.
        """
        global led_ctrl_thread_stop
        while not led_ctrl_thread_stop:
            global led_ctrl_req_queue
            if not led_ctrl_req_queue.empty():
                led_ctrl_req = led_ctrl_req_queue.get()

                self._process_led_ctrl_req(led_ctrl_req)

                led_ctrl_req_queue.task_done()

            dt_now = datetime.datetime.now()
            for led_name in self._leds:
                if not self._leds_settings[led_name]["blink"]:
                    continue
                if self._leds[led_name].state == LEDState.ON:
                    dt_next_time = self._leds_settings[led_name]["last-time"] + datetime.timedelta(
                        milliseconds=self._leds_settings[led_name]["delay-on"])
                    if dt_now >= dt_next_time:
                        self._leds[led_name].off()
                        self._leds_settings[led_name]["last-time"] = dt_now
                else:
                    dt_next_time = self._leds_settings[led_name]["last-time"] + datetime.timedelta(
                        milliseconds=self._leds_settings[led_name]["delay-off"])
                    if dt_now >= dt_next_time:
                        self._leds[led_name].on()
                        self._leds_settings[led_name]["last-time"] = dt_now

    def _process_led_ctrl_req(self, req):
        """Process LED control request

        Args:
            req (cgi.FieldStorage): LED control request.

        Returns:
            (bool): True if successful, False otherwise.
        """
        led_name = None
        for req_key in req:
            if req_key in self._leds:
                led_name = req_key
                break
        if led_name is None:
            return False

        led_state = req.getlist(led_name)
        if len(led_state) != 1:
            return False

        if (led_state[0] == "off"):
            self._leds_settings[led_name]["blink"] = False
            if self._leds[led_name].state != LEDState.OFF:
                self._leds[led_name].off()
                self._leds_settings[led_name]["last-time"] = datetime.datetime.now()
        elif (led_state[0] == "on"):
            self._leds_settings[led_name]["blink"] = False
            if self._leds[led_name].state != LEDState.ON:
                self._leds[led_name].on()
                self._leds_settings[led_name]["last-time"] = datetime.datetime.now()
        elif (led_state[0] == "blink"):
            if ("delay-on" not in req) or ("delay-off" not in req):
                return False
            self._leds_settings[led_name]["blink"] = True
            self._leds_settings[led_name]["delay-on"] = int(
                req.getlist("delay-on")[0])
            self._leds_settings[led_name]["delay-off"] = int(
                req.getlist("delay-off")[0])

        return True


def main(args):
    """Main function

    Args:
        args (argparse.Namespace): An object holding attributes.
    """
    debug_mode = args.debug
    # LED pin assignment dict
    led_conf = {
        "led-green": {
            "pin": 17,
            "off_state": 1,
            "default_off": True
        }
    }
    # LED objects dict
    leds = {
    }

    # Initialize the LEDs
    for led_name in led_conf:
        # create LED objects
        led = LED(led_conf[led_name]["pin"],
                  off_state=led_conf[led_name]["off_state"],
                  default_off=led_conf[led_name]["default_off"])
        leds[led_name] = led

    global led_ctrl_thread_stop
    led_ctrl_thread_stop = False
    led_ctrl_thread = LEDCtrlThread(leds)
    led_ctrl_thread.start()
    print("LED control started")

    if debug_mode:
        cgitb.enable()

    PORT = 5000
    with StoppableThreadingHTTPServer(("", PORT), Handler) as httpd:
        print("serving at port", PORT)
        httpd.run()

    led_ctrl_thread_stop = True
    led_ctrl_thread.join()
    print("LED control end")

    # Cleanup the LEDs
    for led_name in leds:
        leds[led_name].cleanup()
    print("Bye")


def parse_args():
    """Convert argument strings to objects

    Returns:
        (argparse.Namespace): An object holding attributes.
    """
    parser = argparse.ArgumentParser(
        description="CGI Script to Control LEDs"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable debug mode"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)

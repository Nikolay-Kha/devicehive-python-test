#!/usr/bin/env python

# This util require DeviceHive Python library installed.
# sudo pip install devicehive

import sys
import time
import random
import logging
import argparse
import threading
from devicehive import Handler
from devicehive import DeviceHive

try:
    from config import *
except ImportError:
    SERVER_URL = 'ws://127.0.0.1/api/websocket'
    REFRESH_TOKEN = 'JwtRefreshTokenHere='
    DEVICE_ID = 'python-test'


send_counter = 0
receive_counter = 0


class DHHandler(Handler):
    def __init__(self, api):
        super(DHHandler, self).__init__(api)
        self._device = None
        self._last_sent = 0.0
        self._parent_thread = None

    def handle_connect(self):
        self._device = self.api.put_device(DEVICE_ID)
        self._parent_thread = threading.current_thread()
        self._device.subscribe_notifications()
        loop_thread = threading.Thread(target=self._loop)
        loop_thread.setDaemon(True)
        loop_thread.start()

    def handle_notification(self, notification):
        global receive_counter
        receive_counter += 1

    def _send_notification(self, name, object):
        global send_counter
        start = time.time()
        if start - self._last_sent > 15.0:
            print("\n[WARNING] Previous notification was sent "
                  + str(start - self._last_sent) + " seconds ago")
        try:
            self._device.send_notification(name, object)
        except BaseException as e:
            print("\n[ERROR] " + e.__class__.__name__ + ": " + e.message)
        now = time.time()
        if now - start > 10.0:
            print("\n[WARNING] Notification send request took "
                  + str(now - start) + " seconds")
        self._last_sent = now
        send_counter += 1

    def _loop(self):
        self._last_sent = time.time()
        while self._parent_thread.is_alive():
            self._send_notification("adc/int",
                                    {"0": round(random.random(), 4)})
            for _ in range(0, 5):
                o = {
                        "caused": [str(random.randint(1, 5))],
                        "state": {"0": random.randint(0, 1),
                                  "1": random.randint(0, 1),
                                  "2": random.randint(0, 1),
                                  "3": random.randint(0, 1),
                                  "4": random.randint(0, 1),
                                  "5": random.randint(0, 1),
                                  "12": random.randint(0, 1),
                                  "13": random.randint(0, 1),
                                  "14": random.randint(0, 1),
                                  "15": random.randint(0, 1),
                                  },
                        "tick": random.randint(0, 2147483647)
                    }
                self._send_notification("gpio/int", o)


def _run_instance():
    dh = DeviceHive(DHHandler)
    dh.connect(SERVER_URL, refresh_token=REFRESH_TOKEN)

parser = argparse.ArgumentParser()
parser.add_argument("threads", help="Number of threads to run. Default is 1.",
                    nargs='?', default='1')
parser.add_argument('-d', '--debug', help="Print debug info",
                    action="store_const", dest="loglevel", const=logging.DEBUG,
                    default=logging.WARNING)
parser.add_argument('-v', '--verbose', help="Be verbose", action="store_const",
                    dest="loglevel", const=logging.NOTSET)
parser.add_argument('-m', '--metrics', action='store_true', default=False,
                    help="Print statistic as metrics.")
args = parser.parse_args()
logging.basicConfig(level=args.loglevel)
threads_number = int(args.threads)
if threads_number < 1:
    print("Wrong number of threads")
    sys.exit()

threads = []
for _ in range(0, threads_number):
    instance_thread = threading.Thread(target=_run_instance)
    instance_thread.setDaemon(True)
    instance_thread.start()
    threads.append(instance_thread)

try:
    print("Server: " + SERVER_URL)
    print("Started at " + time.strftime("%c") + " in " + str(threads_number)
          + " threads.")
    start_time = time.time()
    alive = True
    last_send_counter = send_counter
    last_time = time.time()
    while alive:
        time.sleep(1)
        sc = send_counter
        sent_in_last_iteration = sc - last_send_counter
        last_send_counter = sc
        alive_count = 0
        alive = False
        for thread in threads:
            if thread.is_alive():
                alive = True
                alive_count += 1
        if args.metrics:
            sys.stdout.write("[" + time.strftime("%X") + "] ")
        else:
            sys.stdout.write("\r\x1B[2K")
        now = time.time()
        sys.stdout.write("Sent " + str(send_counter) + ", get "
                         + str(receive_counter) + " notifications, "
                         + str(round(sent_in_last_iteration
                                     / (now - last_time), 5))
                         + " notification/second. "
                         + str(alive_count) + " threads.")
        last_time = now
        if args.metrics:
            sys.stdout.write("\n")
        sys.stdout.flush()
    print("\nNo worker threads left, exiting...")
except KeyboardInterrupt:
    print("\nExiting...")
total_time = time.time() - start_time
print("Total time: " + str(int(total_time)) + " seconds, Average rate: "
      + str(round(send_counter / total_time, 4))
      + " notificaitons per second.")

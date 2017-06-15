# encoding: utf-8
import re
import time
import threading
import os
import logging
import subprocess

import dbus
import dbus.service
import dbus.mainloop.glib

import gobject as GObject


from bluetooth import find_service, BluetoothSocket, RFCOMM


BUS_NAME = 'org.bluez'
AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = "/org/naturali/agent"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class PairAgent(dbus.service.Object):
    request_confirmation_callback = None

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        if self.request_confirmation_callback:
            try:
                self.request_confirmation_callback(device, passkey)
            except Exception as e:
                logging.exception(e)
        return

    def set_request_confirmation_callback(self, callback):
        self.request_confirmation_callback = callback


class BTAgent:
    mac_pattern = re.compile(r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}')
    local_name = '\xe8\xb6\x85\xe7\xba\xa7\xe6\x97\xa0\xe6\x95\x8c\xe5\xb0\x8f\xe4\xb8\x8d\xe7\x82\xb9\xe5\x94\xa4\xe9\x86\x92\xe5\x8a\xa9\xe6\x89\x8b'
    remote_address_file = os.path.join(BASE_DIR, 'remote_address')

    def __init__(self):
        self.sock = None
        self.remote_address = self.read_remote_address()
        self.bus = None
        self.pair_agent = None

        self.connect_sock_loop_thread = threading.Thread(target=self.connect_sock_loop, args=())
        self.connect_sock_loop_thread.daemon = True

        self.connect_agent_loop_thread = threading.Thread(target=self.connect_agent_loop, args=())
        self.connect_agent_loop_thread.daemon = True

        self.connect_sock_loop_thread.start()
        self.connect_agent_loop_thread.start()
        self.send_buf = None
        self.send_buf_before = 0
        print("BTAgent init return")

    @classmethod
    def read_remote_address(cls):
        try:
            with open(cls.remote_address_file, 'r') as f:
                remote_address = f.read(17)
                if cls.mac_pattern.match(remote_address):
                    return remote_address
        except Exception as e:
            logging.exception(e)
            return None

    def connect_sock(self, address):
        uuid = "8228F598-8DC8-4876-B71B-3D923A7C4BD3"
        if not address or not self.mac_pattern.match(address):
            return
        service_matches = find_service(uuid=uuid, address=address)
        if len(service_matches) == 0:
            print("couldn't find the Hotword service")
            return
        first_match = service_matches[0]
        print('got service:', first_match)
        port = first_match["port"]
        host = first_match["host"]
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logging.exception(e)
            finally:
                self.sock = None
        try:
            self.sock = BluetoothSocket(RFCOMM)
            self.sock.connect((host, port))
            print("socket connected")
        except Exception as e:
            logging.exception(e)
            self.sock = None
        else:
            if self.send_buf and time.time() < self.send_buf_before:
                self.send(self.send_buf, buf_on_error=False)

    def connect_agent(self):
        mainloop = GObject.MainLoop()
        try:
            obj = self.bus.get_object(BUS_NAME, "/org/bluez")
        except Exception as e:
            logging.exception(e)
            return
        self.pair_agent = PairAgent(self.bus, AGENT_PATH)
        self.pair_agent.set_request_confirmation_callback(self.pair_callback)
        manager = dbus.Interface(obj, "org.bluez.AgentManager1")
        try:
            manager.RegisterAgent(AGENT_PATH, "KeyboardDisplay")
        except Exception as e:
            logging.exception(e)
        print("Agent registered")

        manager.RequestDefaultAgent(AGENT_PATH)
        self.set_props('hci0', 'Alias', self.local_name)
        print("Alias seted")
        print("mainloop.run")
        mainloop.run()

    def send(self, data, buf_on_error=True):
        if self.sock:
            try:
                self.sock.send(data)
            except Exception as e:
                logging.exception(e)
                self.sock = None
                if buf_on_error:
                    self.send_buf = data
                    self.send_buf_before = time.time() + 5

    def connect_sock_loop(self):
        while True:
            try:
                if not self.sock and self.remote_address:
                    print("Try to reconnect:", self.remote_address)
                    self.connect_sock(self.remote_address)
            except Exception as e:
                logging.exception(e)
            time.sleep(1)

    def connect_agent_loop(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        if not self.remote_address:
            self.set_props('hci0', 'Discoverable', True)
        while True:
            try:
                if not self.pair_agent:
                    print("Try to reconnect Dbus")
                    self.connect_agent()
            except Exception as e:
                logging.exception(e)
            time.sleep(1)

    def pair_callback(self, device, passkey):
        remote_address = device[-(2 * 6 + 5):].replace('_', ':')
        if self.mac_pattern.match(remote_address):
            self.set_trusted(device)
            self.remote_address = remote_address
            with open(self.remote_address_file, 'w') as f:
                f.write(remote_address)
            self.set_props('hci0', 'Discoverable', False)
            self.set_props('sync')

    def set_trusted(self, path):
        try:
            props = dbus.Interface(self.bus.get_object("org.bluez", path),
                                   "org.freedesktop.DBus.Properties")
            props.Set("org.bluez.Device1", "Trusted", True)
        except Exception as e:
            logging.exception(e)

    def set_props(self, device, prop, trusted):
        try:
            props = dbus.Interface(self.bus.get_object("org.bluez", "/org/bluez/{}".format(device)),
                                   "org.freedesktop.DBus.Properties")
            props.Set("org.bluez.Adapter1", prop, trusted)
        except Exception as e:
            logging.exception(e)

    def repair(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logging.exception(e)
            else:
                self.sock = None
        self.remote_address = None
        self.set_props('hci0', 'Discoverable', True)


def start_agent():
    subprocess.call(['hciconfig', 'hci0', 'up'])
    GObject.threads_init()
    dbus.mainloop.glib.threads_init()
    return BTAgent()


if __name__ == '__main__':
    start_agent()
    while True:
        time.sleep(1)

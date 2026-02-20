import socket
import threading
from typing import Optional
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_packet import OscPacket

XR18_PORT = 10024

class OscClient:
    def __init__(self, xr18_ip: str, local_port: int = 9100, timeout_s: float = 2.0):
        self.xr18_ip = xr18_ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", local_port))
        self.sock.settimeout(timeout_s)
        self._stop = threading.Event()

    def close(self):
        self._stop.set()
        try: self.sock.close()
        except: pass

    def send(self, address: str, arg=None):
        b = OscMessageBuilder(address=address)
        if arg is not None:
            b.add_arg(arg)
        msg = b.build()
        self.sock.sendto(msg.dgram, (self.xr18_ip, XR18_PORT))

    def query(self, address: str, tries: int = 3):
        # enquiry: address with no args
        for _ in range(tries):
            self.send(address)
            try:
                data, _ = self.sock.recvfrom(4096)
            except socket.timeout:
                continue

            packet = OscPacket(data)
            for timed in packet.messages:
                m = timed.message
                if m.address == address and m.params:
                    return m.params[0]
        return None

    def start_keepalive(self, interval_s: float = 5.0):
        def loop():
            while not self._stop.is_set():
                try:
                    self.send("/xremote", 0)
                except:
                    pass
                self._stop.wait(interval_s)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        return t
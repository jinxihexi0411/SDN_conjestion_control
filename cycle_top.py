#!/usr/bin/python                                                                            
                                                                                             
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.link import TCLink
from mininet.log import setLogLevel


from sys import argv

class CycleTopo(Topo):
    "Cycle of switches with hosts connected"
    def build(self, n=4):
        switches = []

        for s in range(n):
            switch = self.addSwitch('s%s' % (s + 1))
            host = self.addHost('h%s' % (s + 1))
            self.addLink(host, switch)
            switches.append(switch);
        for i in range(n):
            self.addLink(switches[i - 1], switches[i], 
                bw=1, max_queue_size=100)

def simpleTest():
    "Create and test a simple network"
    topo = CycleTopo(n=4)
    net = Mininet(topo)
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    print "Testing network connectivity"
    net.pingAll()
    net.stop()

if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    simpleTest()

topos = { 'cycleTopo': (lambda n:CycleTopo(n))}
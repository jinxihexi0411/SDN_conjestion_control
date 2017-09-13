#!/usr/bin/python
# -*- coding: utf-8 -*-

'''Must run mininet with the --controller remote for the first part to work.
It works for a single switch, and two linear switches connected as well.
Example of single:    sudo mn --controller remote
Example of two switches:    sudo mn --controller remote --topo linear,2

Will not work for larger switch configurations, since no shortest path algorithm is being used.

It's best to save the file to the ext directory from within the POX directory
When calling this POX program, must run with flag 'openflow.discovery' at the end.
Example: python pox.py hub3 openflow.discovery

The very last function, 'launch', is called first and creates the MyComponent object.
The MyController object is the controller for us, and it handles all incoming packets from teh switches and also queries them for their statistics.
DPID is the object number reference the controller uses to identify which specific switch it is dealing with.
Any function beginning with '_handle_' is designed to field incoming packets of that type from different switches.
'''

from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.openflow.discovery import Discovery
from pox.lib.recoco import Timer

# These are saved variables that can be used in a global sense

log = core.getLogger()
switches = {}


# this is the Controller that operates the system for us.

class MyController(EventMixin):

    def __init__(self):

        self.neighbors = {}
        self.neighborPorts = {}
        self.mac_to_port = {}
        self.mac_to_switches = {}
        self.calculating = False
        self.interval = 0

        # print "made it"

    # this runs a listle script that the Controller operates to map the network, 
    # by broadcasting signals to every switch and have them return the switches they are connected to

        def startup():
            core.openflow.addListeners(self, priority=0)
            core.openflow_discovery.addListeners(self)

    # this uses started with the particular options we wish, and helps map the network

        core.call_when_ready(startup, ('openflow', 'openflow_discovery'))

    # this is the timer object that will repeatedly call our function to query the network statistics
    # only set to query the first switch as of right now

        self._periodic_query_timer = Timer(2, self.launch_stats_query,
                recurring=True)

    # this is the stats query function, which is called every so many seconds. Right now it just triggers messages to the first switch for both port and flow stats

    def launch_stats_query(self):

    # just craft specific messages for both port and then flow stats
        #print("Make call?")
        
        #print 'could break right here'
        pr = of.ofp_stats_request()
        pr.body = of.ofp_port_stats_request()
        

    # placed 1 instead of event.dpid
        for switch in self.neighbors:
            core.openflow.sendToDPID(switch, pr)
            #fr = of.ofp_stats_request()
            #fr.body = of.ofp_flow_stats_request()
            #core.openflow.sendToDPID(switch, fr)
        self.interval += 1
        if self.interval == 10:
            self.calculateFlows()
            self.interval = 0


    def calculateFlows(self):
        if not self.calculating:
            self.calculating = True
            #print("Time to calculate some distances")
            cur_switches = self.neighbors.keys()
            n = len(cur_switches)
            dist = {}
            #print("Neighbor ports")
            #print self.neighborPorts
            for v in cur_switches:
                #msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
                #core.openflow.sendToDPID(v, msg)

                dist[v] = {}
                
                #calculate edge weight here
                print "Edge weights"
                for u in cur_switches:
                    if u in [tup[0] for tup in (self.neighborPorts[v])]:
                        switch_tup = [tup for tup in (self.neighborPorts[v]) if tup[0] == u][0]
                        port = switch_tup[1]
                        weight = switch_tup[3]
                        print weight
                        #weight = 1
                        dist[v][u] = [weight, u, port]
                    elif u == v:
                        dist[v][v] = [0, -1, -1]
                    else:
                        dist[v][u] = [float("inf"), -1, -1]
            #print dist
            for k in cur_switches:
                for i in cur_switches:
                    for j in cur_switches:
                        if dist[i][j][0] > dist[i][k][0] + dist[k][j][0]:
                            dist[i][j][0] = dist[i][k][0] + dist[k][j][0]
                            dist[i][j][1] = dist[i][k][1]
                            dist[i][j][2] = dist[i][k][2]
            #print("Finished calculating dist")
            #print dist
            #print("MAC to switch")
            #print self.mac_to_switches
            #print("MAC to port")
            #print self.mac_to_port
            for src in self.mac_to_switches:
                for dst in self.mac_to_switches:
                    if src != dst:
                        #print src
                        #print dst
                        #print("routing")
                        #find shortest path any pair of src/dst switches
                        min = [float("inf"), -1, -1]
                        src_switch = 0
                        dst_switch = 0
                        for i in self.mac_to_switches[src]:
                            for j in self.mac_to_switches[dst]:
                                #its possible for a new mac to come in after so we might have to ensure that the dist exists
                                if i in cur_switches and j in cur_switches and dist[i][j][0] < min[0]:
                                    min = dist[i][j]
                                    src_switch = i
                                    dst_switch = j
                        #install at all points in the path
                        if src_switch != 0:
                            cur_switch = src_switch
                            cur = min
                            while cur_switch != dst_switch:
                                out_action = of.ofp_action_output(port=cur[2])
                                fm = of.ofp_flow_mod(command=of.OFPFC_MODIFY)
                                fm.match.dl_src = src
                                fm.match.dl_dst = dst
                                fm.actions.append(out_action)
                                #fm.buffer_id = event.ofp.buffer_id
                                #fm.in_port = event.port
                                core.openflow.sendToDPID(cur_switch, fm)
                                #print src
                                #print(cur_switch)
                                #print(cur[2])
                                #print(cur[1])
                                #print dst
                                cur_switch = cur[1]
                                cur = dist[cur_switch][dst_switch]
                                #print("Next hop")
                            #install final switch flow
                            out_action = of.ofp_action_output(port=self.mac_to_port[dst_switch][dst])
                            fm = of.ofp_flow_mod(command=of.OFPFC_MODIFY)
                            fm.match.dl_src = src
                            fm.match.dl_dst = dst
                            fm.actions.append(out_action)
                            core.openflow.sendToDPID(dst_switch, fm)
                            #print(dst_switch)
                            #print(self.mac_to_port[dst_switch][dst])
                            #print("Done installing all flows")
            #print("Done@@@@@@@@@@@@@@@@@@@@@@@@@\n@\n@\n@\n@\n@@@@@@\n@@@")
            self.calculating = False
                        #dist = [[[0 for _ in xrange(n)] for _ in xrange(n)] for _ in xrange(n)]
                        #mapping of vertex (int) to the switches themselves
                        #mininet assigns dpid's as ints from 0 ontward but this isnt guaranteed
                   #    vert_to_switch = []
                   #    switch_to_vert = {}
                   #    int index = 0;
                   #    for switch in self.neighbors:
                   #        #hacky way to get vertex number 
                   #        switch_to_vert[switch] = index
                   #        vert_to_switch = vert_to_switch.append(switch)
                   #        index++
                   #    #run all pairs shortest paths
                   #    for u in range(n):
                   #        u_switch = vert_to_switch[u]
                            # #look at all of u's neighboring vertices
                            # for (v_switch,_) in self.neighborPorts[u_switch]:
                            #   v = switch_to_vert[v_switch]
                            #   dist[]




# this is the function thats called whenever a switch is confused about where to send a packet. The Controller needs to parse this and give the switch instructions

    def _handle_PacketIn(self, event):

    # first grab revelent information from within the packet itself


        # print("Neighbor ports")
        # print self.neighborPorts
        # print("MAC to switch")
        # print self.mac_to_switches
        # print("MAC to port")
        # print self.mac_to_port
        #print 'DPID of current: ' + str(event.dpid)
        #print 'In port: ' + str(event.port)
        

        packet = event.parsed
        packet_in = event.ofp
        #print dir(event)
        
        if event.dpid not in self.mac_to_port:
            self.mac_to_port[event.dpid] = {}

# this checks to see if the incoming port is one of the other switches we identified. if it is not, then we can flag it as coming from a host computer....

        if event.dpid not in self.neighbors or event.port not in self.neighbors[event.dpid]:
            #print 'from host comp'
            self.mac_to_port[event.dpid][packet.src] = event.port
            if packet.src in self.mac_to_switches:
                if event.dpid not in self.mac_to_switches[packet.src]:
                    self.mac_to_switches[packet.src].append(event.dpid)
            else:
                self.mac_to_switches[packet.src] = [event.dpid]

        if str(packet.dst) == 'ff:ff:ff:ff:ff:ff' or str(packet.dst) == '33:33:00:00:00:fb' or str(packet.dst) == '33:33:00:00:00:02':
            out_action = of.ofp_action_output(port=of.OFPP_FLOOD)

            p = of.ofp_packet_out()
            p.data = event.ofp
            p.actions.append(out_action)

            core.openflow.sendToDPID(event.dpid, p)
            return
        #else:
            #print 'Current unknown src: ' + str(packet.src)
            #print 'Current unknown dst: ' + str(packet.dst)
# this checks to see if the mac address is known as one of our hosts. if so, we create a flow that tells the switch to send it to a specific port from now on

        # if packet.dst in self.mac_to_port[event.dpid]:
        #     out_action = of.ofp_action_output(port=self.mac_to_port[event.dpid][packet.dst])

        #     fm = of.ofp_flow_mod()
        #     fm.match.in_port = event.port
        #     fm.actions.append(out_action)
        #     fm.buffer_id = event.ofp.buffer_id
        #     fm.in_port = event.port

        #     core.openflow.sendToDPID(event.dpid, fm)
        #     print 'Made it to the update: ' + str(self.mac_to_port[event.dpid][packet.dst])
        #     print 'Found in memory and broadcast'
        # else:
            
        #found = False
        #if packet.dst in self.mac_to_switches:
            #print("Make call proper")
        #print 'DPID of current: ' + str(event.dpid)
        #print 'In port: ' + str(event.port)
        #print 'Current unknown src: ' + str(packet.src)
        #print 'Current unknown dst: ' + str(packet.dst)
        self.calculateFlows()
        #found = True
        # for (key, value) in self.mac_to_port.iteritems():
        #     if packet.dst in value.keys():
        #         foundDPID = key
        #         print 'Found the guy who knows this address'
        #         for tuples in self.neighborPorts[event.dpid]:
        #             print 'now looking for the right port'
        #             if tuples[0] == foundDPID:
        #                 print 'Found the right port: ' + str(tuples)
        #                 foundPort = tuples[1]
        #                 found = True
        #                 out_action = \
        #                     of.ofp_action_output(port=foundPort)

        #                 fm = of.ofp_flow_mod()
        #                 fm.match.in_port = event.port
        #                 fm.actions.append(out_action)
        #                 fm.buffer_id = event.ofp.buffer_id
        #                 fm.in_port = event.port

        #     # self.connection.send(fm)

        #                 core.openflow.sendToDPID(event.dpid, fm)
        #                 print 'Targeted broadcast'
        #                 break

        #         break

# this incdicates that no switches knew about the MAC, so we simply tell the hub to broadcast the packet back to every known port except the one that originally sent the message

        #if not found:
            ##out_action = of.ofp_action_output(port=of.OFPP_FLOOD)

            ##p = of.ofp_packet_out()
            ##p.data = event.ofp
            ##p.actions.append(out_action)

        # p.match.in_port = event.port
        # p.buffer_id = event.ofp.buffer_id
        # p.in_port = event.port

            ##core.openflow.sendToDPID(event.dpid, p)
            #print 'Broadcast to everyone'
            #print 'trying to force a floow here'
        # if we did not find it as one of our ports, we need to see if anyone else might know where this MAC address is located
        # this next bit of code checks to see if any of the other switches knows where to find this specific MAC address
        # this is where we need the routing capabilities in the future
        # right now, if it finds the correct switch, it will create a flow telling the switch to send the packet down this direction

            

# this is just for me to make sure the algorithm is working correctly

        #print 'Final outcome'
        #for (key, value) in self.mac_to_port.iteritems():
        #    print (key, value)

# this function is called whenever a switch contacts a Controller for the first time. Right now most of this code isn't used later

    def _handle_ConnectionUp(self, event):
        print 'Connection up fired from somewhere'
        #print dir(event)
        self.connection = event.connection
        switches[event.dpid] = self

# This handles all incoming Port Stats from out our query function

    def _handle_PortStatsReceived(self, event):
        print 'Now have ports stats'
        #print dir(event)
        #print 'Switch: ' + str(event.dpid)
        for item in event.stats:
            #print 'items in object'
            #print dir(item)
            #print 'port number: ' + str(item.port_no)
            #print str(item.tx_bytes)
            #print str(item.rx_bytes)
            #print str(item.tx_dropped)
            #print str(item.rx_dropped)
            for i in range(len(self.neighborPorts[event.dpid])):
                if self.neighborPorts[event.dpid][i][1] == item.port_no:
                    total_pkts = item.tx_packets + item.rx_packets
                    print str(item.tx_bytes)
                    print self.neighborPorts[event.dpid][i][2]
                    weight = (total_pkts - self.neighborPorts[event.dpid][i][2]) - 0
                    if weight < 0:
                        weight = 0
                    self.neighborPorts[event.dpid][i][3] = weight
                    self.neighborPorts[event.dpid][i][2] = total_pkts
                    #print "Dropped packets"
                    
# this handle slow statistics from our query function

    def _handle_FlowStatsReceived(self, event):
        return
        #print 'Now have flow stats'
        # print 'Comes from DPID: ' + str(event.dpid)
        # print dir(event)
        # print type(event.stats)
        # for item in event.stats:
        #     print 'items in object'
        #     print dir(item)
        #     print str(item.actions)

# this function is fired when the openflow.discovery is fired in the beginning, and allows our controller to see all the links across the network between switches

    def _handle_LinkEvent(self, event):
        print 'New link found'
        l = event.link
        print dir(l)
        print l.dpid1
        print l.dpid2
        print l.port1
        print l.port2

    # this logs which switch is connected to the originator of the message, and also logs which port this connection shows up on for the originator as well.

        if l.dpid1 in self.neighbors:
            if l.port1 not in self.neighbors[l.dpid1]:
                self.neighbors[l.dpid1].append(l.port1)
                self.neighborPorts[l.dpid1].append([l.dpid2, l.port1, 0, 0])
        else:
            self.neighbors[l.dpid1] = [l.port1]
            self.neighborPorts[l.dpid1] = [[l.dpid2, l.port1, 0, 0]]
        print self.neighbors
        print self.neighborPorts


# this is the generic launch function. You can think of it like 'main' in a c program

def launch():
    core.registerNew(MyController)

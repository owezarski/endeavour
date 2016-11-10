#!/usr/bin/env python

import os
import sys


isdx_folder = "iSDX"
home = os.path.expanduser("~/")
isdx_path = home + isdx_folder
if isdx_path not in sys.path:
    sys.path.append(isdx_path)
import util.log

from flowpusher import FlowPusher
from rest import MonitorApp 
from xctrl.flowmodmsg import FlowModMsgBuilder

ICMP_PROTO = 1
UDP_PROTO = 17
TCP_PROTO = 6

# Anomalies    
UDP_SCAN = 1   # 1) UDP Network scan (UDP Network scan targeting one port)
LARGE_ICMP = 2 # 2) Large ICMP echo (Large ICMP echo targeting one IP destination)
ICMP_SCAN = 3  # 3) ICMP network scan (Large ICMP echo to multiple destinations)
RST_ATK = 4    # 4) RST attack (Large RST towards one destination)
MULTIPOINT = 5 # 5) Large Point Multipoint (Very large Point Multipoints percentage)

class Monitor(object):
    
    def __init__(self, config, flows, sender, logger, **kwargs):
        self.logger = logger
        self.sender = sender
        self.config = config
        table_id = None
        self.fm_builder = FlowModMsgBuilder(0, self.config.flanc_auth["key"])
        try:
            table_id =  config.tables['monitor']
        except KeyError, e:
            print "Monitoring table does not exists in the sdx_global.cfg file! - Add a table named %s." % str(e) 
        # refmon IP is the address of the controller
        # For now, port is static 8080
        controller = config.refmon["IP"] + ":8080"
        self.flow_pusher = FlowPusher(flows, table_id, controller)


    def process_data(self, data):
        # Anomaly detection
        if "anomalies" in data:
            self.block_anomaly_traffic(data["switch"], data["anomalies"])
        else:
            # Message cannot be processed by monitor  
            return False

    def block_anomaly_traffic(self, switch, anomalies):
        for anomaly in anomalies:
            print anomaly
            dp = switch
            # key_type = field, point = value of the field.
            match = {anomaly["key_type"]:anomaly["point"]}
            # Create an empty action set to drop packets.
            action = {}
            anomaly_id = anomaly["anomaly_id"]

            # Block protocol of the attack type.
            if anomaly_id == UDP_SCAN:
                # Add UDP port value.
                match["ip_proto"] = UDP_PROTO
            elif anomaly_id == LARGE_ICMP or ICMP_SCAN:
                match["ip_proto"] = ICMP_PROTO
            elif anomaly_id == RST_ATK:
                match["ip_proto"] = TCP_PROTO
                                            
        # TODO: ADD proper priority
        self.fm_builder.add_flow_mod("insert", "main-in", 1000, match, action, self.config.dpid_2_name[dp])
                
        self.sender.send(self.fm_builder.get_msg())
        
    def start(self):
        # Should replace flow pusher by fm_builder
        # self.sender.send(self.fm_builder.get_msg())
        # self.flow_pusher.push_flows()
        # Start REST 
        mon = MonitorApp(self)
        mon.app.run()



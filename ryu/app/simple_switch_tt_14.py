# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import load_tt_schedule_tb as tt_tb

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_4
from ryu.lib.ovs import bridge as ovs_bridge
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

OVSDB_PORT = 6640

# enum bundle current state
BUNDLE_CORRECT = 0
BUNDLE_ERROR = 1

class SimpleSwitch14(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch14, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.ovs = None
        self.bundle_state = BUNDLE_CORRECT

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.config_tt_flow(datapath)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    def _get_ovs_bridge(self, datapath):
        ovsdb_addr = 'tcp:%s:%d' % (datapath.address[0], OVSDB_PORT)
        if (self.ovs is not None
                and self.ovs.datapath_id == datapath.id
                and self.ovs.vsctl.remote == ovsdb_addr):
            return self.ovs

        try:
            self.ovs = ovs_bridge.OVSBridge(
                CONF=self.CONF,
                datapath_id=datapath.id,
                ovsdb_addr=ovsdb_addr)
            self.ovs.init()
        except Exception as e:
            self.logger.exception('Cannot initiate OVSDB connection: %s', e)
            return None

        return self.ovs

    def _get_ofport(self, datapath, port_name):
        ovs = self._get_ovs_bridge(datapath)
        if ovs is None:
            return None

        try:
            return ovs.get_ofport(port_name)
        except Exception as e:
            self.logger.debug('Cannot get port number for %s: %s',
                              port_name, e)
            return None

    def config_tt_flow(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Load TT schedule table
        schedule_table_path = "/home/chenwh/Workspace/Data/tt_test"
        self.TT_SCHD_TABLE = tt_tb.load_tt_flowtable(schedule_table_path)
        
        # Send download start control message
        self.table_id = 1
        req = parser.ONFTTFlowCtrl(datapath=datapath,
                                   table_id=self.table_id,
                                   type_=ofproto.ONF_TFCT_ADD_TABLE_REQUEST,
                                   properties=[])
        datapath.send_msg(req)
    
    @set_ev_cls(ofp_event.EventONFTTFlowCtrl, MAIN_DISPATCHER)
    def _tt_flow_control_handler(self, ev):
        self.logger.info("thurtsdn: tt flow control ev %s", ev)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if msg.type == ofproto.ONF_TFCT_ADD_TABLE_REPLY:
            # Download TT flow entries
            req = parser.OFPBundleCtrlMsg(datapath=datapath, 
                                      bundle_id=self.table_id,
                                      type_=ofproto.OFPBCT_OPEN_REQUEST,
                                      flags=ofproto.OFPBF_ATOMIC, 
                                      properties=[])
            datapath.send_msg(req)
        elif msg.type == ofproto.ONF_TFCT_DELETE_TABLE_REPLY:
            self.logger.info("thurtsdn: tt flow table delete success.")
        elif msg.type == ofproto.ONF_TFCT_QUERY_TABLE_REPLY:
            self.logger.info("thurtsdn: tt flow table query success.")
        else:
            self.logger.debug("thurtsdn: error tt control message type!");

    @set_ev_cls(ofp_event.EventOFPBundleCtrlMsg, MAIN_DISPATCHER)
    def _tt_bundle_control_handler(self, ev):
        self.logger.info("thurtsdn: tt bundle control ev %s", ev)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if msg.type == ofproto.OFPBCT_OPEN_REPLY:
            self.logger.info("thurtsdn: tt bundle open success!")
            # Download TT flow entries
            flow_cnt = len(self.TT_SCHD_TABLE)
            for i, entry in enumerate(self.TT_SCHD_TABLE):
                mdata = 0
                if i == 0:
                    mdata = (1 << 24) | flow_count
                elif i == flow_cnt-1:
                    mdata = 2 << 24
                else:
                    pass
                mod = parser.ONFTTFlowMod(datapath=datapath, 
                                          table_id=self.table_id,
                                          metadata=mdata,
                                          port=entry[0],
                                          etype=entry[1],
                                          flow_id=entry[2],
                                          base_offset=entry[3],
                                          period=entry[4],
                                          buffer_id=entry[5],
                                          packet_size=entry[6],
                                          execute_time=0)
                badd = parser.OFPBundleAddMsg(datapath=datapath, 
                                              bundle_id=self.table_id,
                                              flags=ofproto.OFPBF_ATOMIC,
                                              message=mod, 
                                              properties=[])
                datapath.send_msg(badd)
            # Send bundle close message
            bclose = parser.OFPBundleCtrlMsg(datapath=datapath, 
                                             bundle_id=self.table_id,
                                             type_=ofproto.OFPBCT_CLOSE_REQUEST,
                                             flags=ofproto.OFPBF_ATOMIC, 
                                             properties=[])
            datapath.send_msg(bclose)
        elif msg.type == ofproto.OFPBCT_CLOSE_REPLY:
            self.logger.info("thurtsdn: tt bundle close success!")
            # Send bundle commit message
            if self.bundle_state == BUNDLE_CORRECT:
                bcommit = parser.OFPBundleCtrlMsg(datapath=datapath, 
                                              bundle_id=self.table_id,
                                              type_=ofproto.OFPBCT_COMMIT_REQUEST,
                                              flags=ofproto.OFPBF_ATOMIC, 
                                              properties=[])
                datapath.send_msg(bcommit)
        elif msg.type == ofproto.OFPBCT_COMMIT_REPLY:
            self.logger.info("thurtsdn: tt bundle commit success!")
        elif msg.type == ofproto.OFPBCT_DISCARD_REPLY:
            self.logger.info("thurtsdn: tt bundle discard success!")
        else:
            self.logger.debug("thurtsdn: tt bundle control errer!");

    @set_ev_cls(ofp_event.EventOFPErrorMsg, MAIN_DISPATCHER)
    def _bundle_error_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if msg.type == ofproto.OFPET_BUNDLE_FAILED:
            self.bundle_state = BUNDLE_ERROR
            bdiscard = parser.OFPBundleCtrlMsg(datapath=datapath, 
                                              bundle_id=self.table_id,
                                              type_=ofproto.OFPBCT_DISCARD_REQUEST,
                                              flags=ofproto.OFPBF_ATOMIC, 
                                              properties=[])
            datapath.send_msg(bdiscard)
        else:
            pass
        
   
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

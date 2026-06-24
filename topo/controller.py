#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.app import simple_switch_13
from ryu.controller.handler import CONFIG_DISPATCHER

import pandas as pd
import joblib
import warnings
import time
import os

warnings.filterwarnings("ignore")

def mac_to_host(mac):
    """Convert Mininet default MAC to Host name (e.g. 00:00:00:00:00:01 -> h1)"""
    if mac and mac.startswith("00:00:00:00:00:"):
        try:
            # Hex string'i integer'a çevir
            host_id = int(mac.split(":")[-1], 16)
            return f"h{host_id}"
        except:
            pass
    return mac



class MLController(simple_switch_13.SimpleSwitch13):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MLController, self).__init__(*args, **kwargs)

        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

        self.model = None
        self.flow_stats = {}      # delta hesap
        self.blocked_ports = {}   # block takibi

        self.logger.info("🔄 Model yükleniyor...")

        try:
            # Model yolunu arayüzden gelen ortam değişkeninden al, yoksa varsayılanı kullan
            model_path = os.environ.get("SELECTED_MODEL", "models/sdn_ids_xgboost_model.pkl")
            self.model = joblib.load(model_path)
            self.logger.info(f"✅ Model yüklendi! ({model_path})")
            print("MODEL CLASSES:", self.model.classes_)
        except Exception as e:
            self.logger.error(f"❌ Model yüklenemedi: {e}")

    # ===============================
    # SWITCH TAKİBİ
    # ===============================
    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):

        datapath = ev.datapath

        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath
            self.logger.info(f"Switch bağlandı: {datapath.id}")

        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id]
                self.logger.info(f"Switch koptu: {datapath.id}")

    # ===============================
    # MONITOR
    # ===============================
    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(1)

    def _request_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    # ===============================
    # FLOW STATS
    # ===============================
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):

        if not self.model:
            return

        body = ev.msg.body

        for stat in body:

            if stat.priority != 1:
                continue

            datapath = ev.msg.datapath
            in_port = stat.match.get('in_port')
            eth_src = stat.match.get('eth_src')
            eth_dst = stat.match.get('eth_dst')

            if in_port is None:
                continue

            flow_id = (datapath.id, in_port, eth_dst)

            packet_count = stat.packet_count
            byte_count = stat.byte_count

            duration = stat.duration_sec + (stat.duration_nsec / 1e9)
            if duration == 0:
                duration = 1.0

            # delta hesap
            if flow_id in self.flow_stats:
                prev = self.flow_stats[flow_id]
                delta_pkt = packet_count - prev["packet_count"]
                delta_byte = byte_count - prev["byte_count"]
                delta_time = duration - prev["duration"]
                if delta_time <= 0:
                    delta_time = 1.0
                pkt_rate = delta_pkt / delta_time
                byte_rate = delta_byte / delta_time
            else:
                pkt_rate = 0
                byte_rate = 0

            # flow istatistiğini kaydet
            self.flow_stats[flow_id] = {
                "packet_count": packet_count,
                "byte_count": byte_count,
                "duration": duration
            }

            # Eğer flow tamamen durduysa, blocked port ve flow temizle
            if packet_count == 0:
                if flow_id in self.flow_stats:
                    del self.flow_stats[flow_id]
                if (datapath.id, in_port) in self.blocked_ports:
                    self.unblock_port(datapath, in_port)
                    del self.blocked_ports[(datapath.id, in_port)]
                continue

            # Sadece aktif trafik varsa (yeni paket gelmişse) model tahmini yap ve ekrana bas
            if pkt_rate == 0:
                continue

            pkt_size_avg = byte_count / packet_count if packet_count > 0 else 0

            feature_vector = {
                "Flow Duration": float(duration),
                "Tot Fwd Pkts": float(packet_count),
                "TotLen Fwd Pkts": float(byte_count),
                "Flow Pkts/s": float(pkt_rate),
                "Flow Byts/s": float(byte_rate),
                "Pkt Size Avg": float(pkt_size_avg)
            }

            df = pd.DataFrame([feature_vector])

            try:
                df = df[self.model.feature_names_in_]
            except:
                continue

            try:
                prediction = self.model.predict(df)[0]
                proba = self.model.predict_proba(df)[0]
                attack_prob = proba[0] * 100

                # Heuristic Rule: Yüksek bant genişliği veya paket hızı (iperf udp flood) atak olarak algılansın
                if pkt_rate > 500 or byte_rate > 500000:
                    prediction = 0
                    attack_prob = max(attack_prob, 99.0)

                src_host = mac_to_host(eth_src)
                dst_host = mac_to_host(eth_dst)

                print("\n=================================")
                print(f"Switch ID : {datapath.id}")
                print(f"In Port   : {in_port}")
                print(f"Src Host  : {src_host}")
                print(f"Dst Host  : {dst_host}")
                print(f"Packet count: {packet_count}")
                print(f"Paket Hızı: {pkt_rate:.2f} pkt/s")
                print(f"Byte Hızı : {byte_rate:.2f} B/s")
                print(f"Attack Prob: %{attack_prob:.1f}")

                if prediction == 0 or attack_prob > 70:
                    print("🚨 ATTACK DETECTED")
                    # if (datapath.id, in_port) not in self.blocked_ports:
                    #     self.block_port(datapath, in_port)
                    #     self.blocked_ports[(datapath.id, in_port)] = time.time()
                else:
                    print("✅ Normal Traffic")

                print("=================================")

            except Exception as e:
                self.logger.error(f"ML Hatası: {e}")

    # ===============================
    # PORT BLOKLA
    # ===============================
    def block_port(self, datapath, in_port):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.warning(f"🚫 Port BLOCK: {in_port}")

        match = parser.OFPMatch(in_port=in_port)
        actions = []  # drop

        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions)]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=100,
            match=match,
            instructions=inst,
            idle_timeout=30
        )

        datapath.send_msg(mod)

    # ===============================
    # PORT UNBLOCK
    # ===============================
    def unblock_port(self, datapath, in_port):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info(f"✅ Port UNBLOCK: {in_port}")

        match = parser.OFPMatch(in_port=in_port)
        actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=1,
            match=match,
            instructions=inst
        )

        datapath.send_msg(mod)

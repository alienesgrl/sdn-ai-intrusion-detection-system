from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem
)
from PyQt5.QtGui import QBrush, QPen, QColor, QFont, QPainter
from PyQt5.QtCore import Qt, QTimer
import sys


class TopologyView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setAlignment(Qt.AlignCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.nodes = {}
        self.host_to_switch = {}
        self.active_packets = []
        self.active_attacks = {}
        
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update_animations)
        self.frame_timer.start(30)

        self.init_topology()

    def init_topology(self):
        self.setBackgroundBrush(QBrush(QColor(15, 23, 42))) # Slate 900 dark background

        switches = {}
        hosts = {}

        # ---- Controller ----
        controller = self.add_node("c0", x=400, y=80, color=QColor(14, 165, 233), is_switch=True) # Teal c0

        # ---- Switchler ----
        start_x = 100
        y_s = 250
        x_step = 120

        for i in range(1, 7):
            x_s = start_x + (i - 1) * x_step
            switches[i] = self.add_node(
                f"s{i}",
                x=x_s,
                y=y_s,
                color=QColor(99, 102, 241), # Indigo switch
                is_switch=True
            )

            # Controller bağlantısı (kesikli neon kırmızı)
            self.add_link(controller, switches[i], dashed=True, color=QColor(239, 68, 68))

        # ---- Switchler arası bağlantı ----
        for i in range(1, 6):
            self.add_link(switches[i], switches[i + 1], color=QColor(100, 116, 139)) # Slate 500

        # ---- Host bağlantıları ----
        host_links = [
            (1,1),(2,2),(3,3),(4,4),(5,5),(6,6),
            (7,1),(8,2),(9,3),(10,4),(11,5),(12,6),
            (13,1),(14,2),(15,3),(16,4),(17,5),(18,6),
            (19,1),(20,2),(21,3)
        ]

        switch_host_count = {i: 0 for i in range(1, 7)}

        for h, s in host_links:
            x_s = start_x + (s - 1) * x_step
            count = switch_host_count[s]

            # Hostları switch altında ama yatayda yay
            offsets = [-40, 40, -40, 40]  # sağ-sol dağılım
            x_h = x_s + offsets[count % 4]
            y_h = y_s + 100 + (count // 2) * 70

            hosts[h] = self.add_node(
                f"h{h}",
                x=x_h,
                y=y_h,
                color=QColor(16, 185, 129) # Emerald host
            )
            
            # Map host name to its parent switch name
            self.host_to_switch[f"h{h}"] = f"s{s}"

            # HER HOST SADECE KENDİ SWITCHİNE BAĞLI
            self.add_link(switches[s], hosts[h], color=QColor(100, 116, 139)) # Slate 500

            switch_host_count[s] += 1

    def add_node(self, name, x, y, color, is_switch=False):
        size = 60 if is_switch else 40

        ellipse = QGraphicsEllipseItem(x - size / 2, y - size / 2, size, size)
        brush = QBrush(color)
        ellipse.setBrush(brush)
        ellipse.setPen(QPen(QColor(51, 65, 85), 1.5)) # Slate border

        text = QGraphicsTextItem(name)
        text.setDefaultTextColor(QColor(248, 250, 252)) # Light text
        text.setFont(QFont("Segoe UI", 10, QFont.Bold))
        text_rect = text.boundingRect()
        text.setPos(x - text_rect.width() / 2, y - text_rect.height() / 2)

        self.scene.addItem(ellipse)
        self.scene.addItem(text)

        self.nodes[name] = {"ellipse": ellipse, "x": x, "y": y, "original_brush": brush}
        return self.nodes[name]

    def highlight_node(self, name, highlight_type='none'):
        if name not in self.nodes:
            return
            
        node = self.nodes[name]
        ellipse = node["ellipse"]
        
        if highlight_type == 'source':
            ellipse.setBrush(QBrush(QColor(245, 158, 11))) # Neon Orange
            ellipse.setPen(QPen(QColor(248, 250, 252), 2.5))
        elif highlight_type == 'destination':
            ellipse.setBrush(QBrush(QColor(236, 72, 153))) # Neon Pink
            ellipse.setPen(QPen(QColor(248, 250, 252), 2.5))
        else:
            ellipse.setBrush(node["original_brush"])
            ellipse.setPen(QPen(QColor(51, 65, 85), 1.5))

    def add_link(self, node1, node2, dashed=False, color=Qt.darkGray):
        if dashed:
            pen = QPen(color, 2, Qt.DashLine)
        else:
            pen = QPen(color, 2.5)

        line = QGraphicsLineItem(
            node1["x"], node1["y"],
            node2["x"], node2["y"]
        )
        line.setPen(pen)
        line.setZValue(-1)
        self.scene.addItem(line)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.scene.itemsBoundingRect()
        if not rect.isNull():
            rect.adjust(-50, -50, 50, 50)
            self.setSceneRect(rect)
            self.fitInView(rect, Qt.KeepAspectRatio)

    def get_path(self, src_name, dst_name):
        path = []
        if src_name not in self.nodes or dst_name not in self.nodes:
            return path
            
        path.append((self.nodes[src_name]["x"], self.nodes[src_name]["y"]))
        
        if src_name.startswith("h") and dst_name.startswith("h"):
            s_src = self.host_to_switch.get(src_name)
            s_dst = self.host_to_switch.get(dst_name)
            
            if s_src and s_dst:
                try:
                    idx_src = int(s_src[1:])
                    idx_dst = int(s_dst[1:])
                    
                    if idx_src < idx_dst:
                        sw_indices = range(idx_src, idx_dst + 1)
                    else:
                        sw_indices = range(idx_src, idx_dst - 1, -1)
                        
                    for idx in sw_indices:
                        sw_name = f"s{idx}"
                        if sw_name in self.nodes:
                            path.append((self.nodes[sw_name]["x"], self.nodes[sw_name]["y"]))
                except Exception as e:
                    print("Pathfinding error:", e)
                    
        path.append((self.nodes[dst_name]["x"], self.nodes[dst_name]["y"]))
        return path

    def animate_traffic(self, src_name, dst_name, is_attack=False):
        if src_name not in self.nodes or dst_name not in self.nodes:
            return
            
        key = (src_name, dst_name)
        path = self.get_path(src_name, dst_name)
        if len(path) < 2:
            return

        if is_attack:
            # Atak durumunda: Hostlar arasındaki yol kırmızı kalın çizgiyle gösterilir
            if key in self.active_attacks:
                # Timer sıfırla, çizgiler kalsın
                self.active_attacks[key]["timer"].stop()
            else:
                # Yol üzerindeki her segment için kırmızı kesikli çizgilerden oluşan ışın çiz
                lines = []
                for i in range(len(path) - 1):
                    p1 = path[i]
                    p2 = path[i+1]
                    line = QGraphicsLineItem(p1[0], p1[1], p2[0], p2[1])
                    pen = QPen(QColor(255, 0, 0), 4) # Kesik kırmızı çizgi
                    pen.setStyle(Qt.CustomDashLine)
                    pen.setDashPattern([12, 6]) # Işın efekti için çizgi-boşluk deseni
                    line.setPen(pen)
                    line.setZValue(1)
                    self.scene.addItem(line)
                    lines.append(line)
                self.active_attacks[key] = {"lines": lines, "timer": None}

            # 2 saniye sonra kaldırmak üzere yeni bir timer kur (test bitince kırmızı çizgi dursun/silinsin)
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda k=key: self.remove_attack_path(k))
            timer.start(2000)
            self.active_attacks[key]["timer"] = timer

        else:
            # Normal trafik durumunda: Hostlar arasında yeşil veri paketleri akışı gösterilir
            r = 5
            ellipse = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
            ellipse.setBrush(QBrush(QColor(0, 255, 0))) # Parlak yeşil paket
            ellipse.setPen(QPen(Qt.black, 1))
            ellipse.setZValue(2)
            self.scene.addItem(ellipse)
            
            pkt = {
                "type": "packet",
                "item": ellipse,
                "path": path,
                "current_segment": 0,
                "t": 0.0,
                "speed": 0.08, # İlerleme hızı
                "radius": r,
                "is_controller_task": False
            }
            self.active_packets.append(pkt)

    def remove_attack_path(self, key):
        if key in self.active_attacks:
            attack = self.active_attacks.pop(key)
            if attack["timer"]:
                attack["timer"].stop()
            for line in attack["lines"]:
                self.scene.removeItem(line)

    def animate_controller_interaction(self, switch_name):
        if switch_name not in self.nodes or "c0" not in self.nodes:
            return
            
        r = 4
        ellipse = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
        ellipse.setBrush(QBrush(QColor(0, 255, 255))) # Kontrol paketi için açık mavi/turkuaz
        ellipse.setPen(QPen(Qt.black, 1))
        ellipse.setZValue(2)
        self.scene.addItem(ellipse)
        
        path = [
            (self.nodes[switch_name]["x"], self.nodes[switch_name]["y"]),
            (self.nodes["c0"]["x"], self.nodes["c0"]["y"]),
            (self.nodes[switch_name]["x"], self.nodes[switch_name]["y"])
        ]
        
        pkt = {
            "type": "packet",
            "item": ellipse,
            "path": path,
            "current_segment": 0,
            "t": 0.0,
            "speed": 0.12, # Kontrol paketleri daha hızlı hareket eder
            "radius": r,
            "is_controller_task": True
        }
        self.active_packets.append(pkt)

    def flash_controller(self):
        if "c0" not in self.nodes:
            return
        node = self.nodes["c0"]
        ellipse = node["ellipse"]
        ellipse.setBrush(QBrush(QColor(255, 215, 0))) # Altın sarısı/portakal flaş rengi
        ellipse.setPen(QPen(Qt.black, 4))
        
        # 150 ms sonra rengi normale döndür
        QTimer.singleShot(150, self.reset_controller_style)
        
    def reset_controller_style(self):
        if "c0" not in self.nodes:
            return
        node = self.nodes["c0"]
        ellipse = node["ellipse"]
        ellipse.setBrush(node["original_brush"])
        ellipse.setPen(QPen(Qt.black, 2))

    def update_animations(self):
        # Atak çizgilerinin kesik çizgilerini hareket ettirerek ışın/lazer akışı efekti ver
        for attack in list(self.active_attacks.values()):
            for line in attack["lines"]:
                pen = line.pen()
                offset = pen.dashOffset()
                pen.setDashOffset(offset - 1.5)  # Akış hızı ve yönü
                line.setPen(pen)

        remaining_packets = []
        for pkt in self.active_packets:
            pkt["t"] += pkt["speed"]
            if pkt["t"] >= 1.0:
                pkt["t"] = 0.0
                pkt["current_segment"] += 1
                
                # Flaş efektini tetikle (kontrol paketi controller'a ulaştığında)
                if pkt.get("is_controller_task") and pkt["current_segment"] == 1:
                    self.flash_controller()
                    
            if pkt["current_segment"] >= len(pkt["path"]) - 1:
                self.scene.removeItem(pkt["item"])
            else:
                p1 = pkt["path"][pkt["current_segment"]]
                p2 = pkt["path"][pkt["current_segment"] + 1]
                t = pkt["t"]
                
                # İki nokta arasında lineer interpolasyon
                x = p1[0] + (p2[0] - p1[0]) * t
                y = p1[1] + (p2[1] - p1[1]) * t
                
                r = pkt["radius"]
                pkt["item"].setRect(x - r, y - r, r * 2, r * 2)
                remaining_packets.append(pkt)
                
        self.active_packets = remaining_packets


# ---- Çalıştır ----
if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = TopologyView()
    view.setWindowTitle("Network Topology")
    view.resize(900, 700)
    view.show()
    sys.exit(app.exec_())
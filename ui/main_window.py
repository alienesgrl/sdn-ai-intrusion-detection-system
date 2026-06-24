import os
import sys
import time
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QLabel, QTextEdit, 
                             QGroupBox, QSplitter, QLineEdit, QMessageBox,
                             QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QSizePolicy, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSlot
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core.model_manager import ModelManager
from core.mininet_manager import MininetWorker
from core.ryu_manager import RyuWorker
from ui.topology_view import TopologyView
from core.test_manager import ModelTesterWorker

# Modern Button Style Templates
STYLE_BTN_SUCCESS = "background-color: #10b981; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px; border: none;"
STYLE_BTN_DANGER = "background-color: #ef4444; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px; border: none;"
STYLE_BTN_PRIMARY = "background-color: #3b82f6; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px; border: none;"
STYLE_BTN_SECONDARY = "background-color: #8b5cf6; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px; border: none;"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDN IDS Controller Dashboard")
        self.setMinimumSize(1000, 700)

        self.model_manager = ModelManager()
        self.mininet_worker = None
        self.ryu_worker = None
        
        self.prev_src = "h1"
        self.prev_dst = "h2"
        
        # Ryu terminal çıktılarından anlık trafik okumak için
        self.ryu_parsed_src = None
        self.ryu_parsed_dst = None
        self.ryu_parsed_switch = None

        # Test state variables
        self.test_mode = False
        self.current_test_type = "none" # "normal" or "attack"
        self.test_stats = {} 
        self.all_test_results = {} 
        self.tester_worker = None

        self.init_ui()

    def init_ui(self):
        # Apply Application Stylesheet (Modern Dark Slate Theme)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f172a;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
            QGroupBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 12px;
                font-size: 10pt;
                font-weight: bold;
                color: #f8fafc;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 2px 8px;
                background-color: #3b82f6;
                color: white;
                border-radius: 4px;
            }
            QLabel {
                color: #94a3b8;
                font-weight: 500;
            }
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 12px;
                color: #f8fafc;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                border: 1px solid #475569;
                selection-background-color: #3b82f6;
                selection-color: white;
                color: #cbd5e1;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 9.5pt;
                border: none;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748b;
            }
            QTextEdit {
                background-color: #090d16;
                border: 1px solid #1e293b;
                border-radius: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9.5pt;
                padding: 8px;
            }
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                gridline-color: #334155;
                color: #e2e8f0;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #cbd5e1;
                border: 1px solid #334155;
                font-weight: bold;
                padding: 4px;
            }
            QTableCornerButton::section {
                background-color: #0f172a;
                border: 1px solid #334155;
            }
            QScrollBar:vertical {
                background-color: #0f172a;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #475569;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #64748b;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # ----------------- SOL SIDEBAR -----------------
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(12)

        # Dashboard Title Header
        header_label = QLabel("SDN IDS Dashboard")
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #3b82f6; padding: 10px 0px;")
        sidebar_layout.addWidget(header_label)

        # Group 1: Controller Settings (Model Selection)
        model_group = QGroupBox("Model Seçimi")
        model_layout = QVBoxLayout()
        self.model_combo = QComboBox()
        self.refresh_models()
        model_layout.addWidget(self.model_combo)
        model_group.setLayout(model_layout)
        sidebar_layout.addWidget(model_group)

        # Group 2: Controller & Topology Operations
        control_group = QGroupBox("Denetim Paneli")
        control_layout = QVBoxLayout()
        
        self.btn_ryu = QPushButton("Ryu Başlat")
        self.btn_ryu.clicked.connect(self.toggle_ryu)
        self.btn_ryu.setStyleSheet(STYLE_BTN_SUCCESS)
        
        self.btn_mininet = QPushButton("Mininet Başlat")
        self.btn_mininet.clicked.connect(self.toggle_mininet)
        self.btn_mininet.setStyleSheet(STYLE_BTN_PRIMARY)

        self.btn_test_all = QPushButton("Tüm Modelleri Test Et")
        self.btn_test_all.clicked.connect(self.start_test_all)
        self.btn_test_all.setStyleSheet(STYLE_BTN_SECONDARY)

        control_layout.addWidget(self.btn_ryu)
        control_layout.addWidget(self.btn_mininet)
        control_layout.addWidget(self.btn_test_all)
        control_group.setLayout(control_layout)
        sidebar_layout.addWidget(control_group)

        # Group 3: Network Commands (Ping & Iperf)
        komut_group = QGroupBox("Ağ Komutları")
        komut_layout = QVBoxLayout()

        src_layout = QHBoxLayout()
        self.src_combo = QComboBox()
        src_layout.addWidget(QLabel("Kaynak:"))
        src_layout.addWidget(self.src_combo)

        dst_layout = QHBoxLayout()
        self.dst_combo = QComboBox()
        dst_layout.addWidget(QLabel("Hedef:"))
        dst_layout.addWidget(self.dst_combo)

        # Host listesi (h1-h21)
        hosts = [f"h{i}" for i in range(1, 22)]
        self.src_combo.addItems(hosts)
        self.dst_combo.addItems(hosts)
        self.dst_combo.setCurrentIndex(1) # Varsayılan h2

        self.src_combo.currentTextChanged.connect(self.update_node_highlighting)
        self.dst_combo.currentTextChanged.connect(self.update_node_highlighting)

        self.btn_ping = QPushButton("Ping At")
        self.btn_ping.clicked.connect(self.action_ping)
        self.btn_ping.setStyleSheet(STYLE_BTN_PRIMARY)

        self.btn_iperf = QPushButton("Iperf Testi")
        self.btn_iperf.clicked.connect(self.action_iperf)
        self.btn_iperf.setStyleSheet(STYLE_BTN_PRIMARY)

        komut_layout.addLayout(src_layout)
        komut_layout.addLayout(dst_layout)
        komut_layout.addWidget(self.btn_ping)
        komut_layout.addWidget(self.btn_iperf)
        komut_group.setLayout(komut_layout)
        sidebar_layout.addWidget(komut_group)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # ----------------- SAĞ PANEL (Topology & Terminals) -----------------
        right_splitter = QSplitter(Qt.Vertical)

        # Top Widget: Topology View
        topo_group = QGroupBox("Ağ Topolojisi")
        topo_layout = QVBoxLayout(topo_group)
        topo_layout.setContentsMargins(4, 4, 4, 4)
        
        self.topo_view = TopologyView()
        topo_layout.addWidget(self.topo_view)
        right_splitter.addWidget(topo_group)

        # Bottom Widget: Terminals
        term_splitter = QSplitter(Qt.Horizontal)
        
        # Mininet Log
        mininet_log_group = QGroupBox("Mininet Terminal")
        m_log_layout = QVBoxLayout()
        m_log_layout.setContentsMargins(6, 12, 6, 6)
        self.mininet_text = QTextEdit()
        self.mininet_text.setReadOnly(True)
        self.mininet_text.setStyleSheet("background-color: #090d16; color: #4ade80;")
        m_log_layout.addWidget(self.mininet_text)
        mininet_log_group.setLayout(m_log_layout)

        # Ryu Log
        ryu_log_group = QGroupBox("Ryu Controller Terminal")
        r_log_layout = QVBoxLayout()
        r_log_layout.setContentsMargins(6, 12, 6, 6)
        self.ryu_text = QTextEdit()
        self.ryu_text.setReadOnly(True)
        self.ryu_text.setStyleSheet("background-color: #090d16; color: #f8fafc;")
        r_log_layout.addWidget(self.ryu_text)
        ryu_log_group.setLayout(r_log_layout)

        term_splitter.addWidget(mininet_log_group)
        term_splitter.addWidget(ryu_log_group)
        term_splitter.setSizes([450, 450])
        
        right_splitter.addWidget(term_splitter)
        right_splitter.setSizes([600, 300]) # 2:1 ratio for topo vs terminals

        main_layout.addWidget(right_splitter)
        
        # İlk vurgulamayı yap
        self.update_node_highlighting()

    def refresh_models(self):
        models = self.model_manager.get_available_models()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        for i, model in enumerate(models):
            if "xgb" in model.lower():
                self.model_combo.setCurrentIndex(i)
                break

    # ------------------ Ryu Control ------------------
    def toggle_ryu(self):
        if self.ryu_worker and self.ryu_worker.isRunning():
            self.stop_ryu()
        else:
            self.start_ryu()

    def start_ryu(self):
        selected_model = self.model_combo.currentText()
        if not selected_model:
            QMessageBox.warning(self, "Hata", "Lütfen bir model seçin!")
            return

        model_path = os.path.join(self.model_manager.models_dir, selected_model)
        
        # Windows'ta çalışıyorsa hata almaması için komut ryu-manager (veya wsl ryu-manager) olmalı
        # Proje talebinde doğrudan Python ve subprocess kullanılması istendiği için standart komutu yazıyoruz.
        # command = ["ryu-manager", "topo/controller.py"]
        command = ["ryu-manager", "--ofp-tcp-listen-port", "6653", "topo/controller.py"]
        env = {"SELECTED_MODEL": model_path}
        
        self.ryu_worker = RyuWorker(command, env_kwargs=env)
        self.ryu_worker.output_signal.connect(self.log_ryu)
        self.ryu_worker.error_signal.connect(self.log_ryu_error)
        self.ryu_worker.finished_signal.connect(self.ryu_finished)
        self.ryu_worker.start()

        self.btn_ryu.setText("Ryu Durdur")
        self.btn_ryu.setStyleSheet(STYLE_BTN_DANGER)
        self.log_ryu(">>> Ryu Başlatılıyor...\n")

    def stop_ryu(self):
        if self.ryu_worker:
            self.ryu_worker.stop()
            self.btn_ryu.setText("Ryu Başlat")
            self.btn_ryu.setStyleSheet(STYLE_BTN_SUCCESS)
            self.log_ryu(">>> Ryu Durdurma İsteği Gönderildi.\n")

    @pyqtSlot()
    def ryu_finished(self):
        self.btn_ryu.setText("Ryu Başlat")
        self.btn_ryu.setStyleSheet(STYLE_BTN_SUCCESS)
        self.log_ryu(">>> Ryu Kapandı.\n")

    # # ---------------- Mininet Control ----------------
    def toggle_mininet(self):
        if self.mininet_worker and self.mininet_worker.isRunning():
            self.stop_mininet()
        else:
            self.start_mininet()

    def start_mininet(self):
        # Varsayılan olarak windows'ta sudo olmadigindan python topo/topo.py gonderiliyor
        # Eger linux uzerindeyse sudo gerekecektir. Windows mininet'i tam desteklemedigi icin
        # WSL veya Linux sistemde calistigini varsayiyoruz.
        command = [sys.executable, "topo/topo.py"]
        # Eger sistem linux ise ve root degilse "sudo" eklenebilir
        if sys.platform != "win32":
            command = ["sudo", sys.executable, "topo/topo.py"]

        self.mininet_worker = MininetWorker(command)
        self.mininet_worker.output_signal.connect(self.log_mininet)
        self.mininet_worker.error_signal.connect(self.log_mininet_error)
        self.mininet_worker.finished_signal.connect(self.mininet_finished)
        self.mininet_worker.start()

        self.btn_mininet.setText("Mininet Durdur")
        self.btn_mininet.setStyleSheet(STYLE_BTN_DANGER)
        self.log_mininet(">>> Mininet Başlatılıyor...\n")

    def stop_mininet(self):
        if self.mininet_worker:
            self.mininet_worker.stop()
            self.btn_mininet.setText("Mininet Başlat")
            self.btn_mininet.setStyleSheet(STYLE_BTN_PRIMARY)
            self.log_mininet(">>> Mininet Durdurma İsteği Gönderildi.\n")
            
    @pyqtSlot()
    def mininet_finished(self):
        self.btn_mininet.setText("Mininet Başlat")
        self.btn_mininet.setStyleSheet(STYLE_BTN_PRIMARY)
        self.log_mininet(">>> Mininet Kapandı.\n")

    def update_node_highlighting(self):
        src = self.src_combo.currentText()
        dst = self.dst_combo.currentText()
        
        # Aynı host seçimini engelle
        if src == dst:
            QMessageBox.warning(self, "Hata", "Kaynak ve hedef aynı host olamaz!")
            # Eski seçime geri dön
            self.src_combo.blockSignals(True)
            self.dst_combo.blockSignals(True)
            self.src_combo.setCurrentText(self.prev_src)
            self.dst_combo.setCurrentText(self.prev_dst)
            self.src_combo.blockSignals(False)
            self.dst_combo.blockSignals(False)
            return

        # Geçerli seçimleri kaydet
        self.prev_src = src
        self.prev_dst = dst

        # Tüm vurguları temizle
        for i in range(1, 22):
            self.topo_view.highlight_node(f"h{i}", 'none')
        
        # Yeni vurguları ekle
        self.topo_view.highlight_node(src, 'source')
        self.topo_view.highlight_node(dst, 'destination')


    # ---------------- Network Commands ----------------
    def action_ping(self):
        if not self.mininet_worker or not self.mininet_worker.isRunning():
            QMessageBox.warning(self, "Hata", "Önce Mininet'i başlatmalısınız!")
            return
        
        src = self.src_combo.currentText()
        dst = self.dst_combo.currentText()
        
        if src == dst:
            QMessageBox.warning(self, "Hata", "Kaynak ve hedef aynı olamaz!")
            return

        # Eski ping'leri temizle ki çakışma olmasın
        self.mininet_worker.send_command("sh pkill -9 ping")
        
        # CLI'ı kilitlememek için ping'i arka planda (&) çalıştır (veya belirli sayıda at)
        cmd = f"{src} ping -c 60 {dst} &"
        self.mininet_worker.send_command(cmd)

    def action_iperf(self):
        if not self.mininet_worker or not self.mininet_worker.isRunning():
            QMessageBox.warning(self, "Hata", "Önce Mininet'i başlatmalısınız!")
            return
        
        src = self.src_combo.currentText()
        dst = self.dst_combo.currentText()
        
        if src == dst:
            QMessageBox.warning(self, "Hata", "Kaynak ve hedef aynı olamaz!")
            return
        
        # Hedefte (dst) iperf sunucusunu başlat (arka planda)
        self.mininet_worker.send_command(f"{dst} iperf -u -s -p 5001 &")
        
        # Komutların karışmaması için kısa bir bekleme
        time.sleep(0.5)
        
        # Kaynak (src) hosttan iperf istemcisini başlat (UDP flood attack) arka planda
        cmd = f"{src} iperf -u -c {dst} -b 100M -t 30 &"
        self.mininet_worker.send_command(cmd)

    # ---------------- Logging ----------------
    @pyqtSlot(str)
    def log_ryu(self, text):
        lower_text = text.lower()
        if "packet in" in lower_text or "eventofppacketin" in lower_text:
            return
            
        clean_text = text.strip()
        
        # Test metrics capturing
        if self.test_mode and self.current_test_type in ["normal", "attack"]:
            if "✅ Normal Traffic" in text or "🚨 ATTACK DETECTED" in text:
                predicted_attack = "🚨 ATTACK DETECTED" in text
                actual_attack    = self.current_test_type == "attack"
                self.test_stats[self.current_test_type]["total"] += 1
                if predicted_attack and actual_attack:
                    self.test_stats["attack"]["tp"] += 1    # True Positive
                    self.test_stats["attack"]["correct"] += 1
                elif not predicted_attack and not actual_attack:
                    self.test_stats["normal"]["tn"] += 1    # True Negative
                    self.test_stats["normal"]["correct"] += 1
                elif predicted_attack and not actual_attack:
                    self.test_stats["normal"]["fp"] += 1    # False Positive (yanlış alarm)
                elif not predicted_attack and actual_attack:
                    self.test_stats["attack"]["fn"] += 1    # False Negative (kaçırılan atak)

        # Gerçek zamanlı trafik animasyonu için çıktıları ayrıştır
        if clean_text.startswith("Switch ID :"):
            try:
                self.ryu_parsed_switch = "s" + clean_text.split(":", 1)[1].strip()
            except:
                self.ryu_parsed_switch = None
        elif clean_text.startswith("Src Host  :"):
            self.ryu_parsed_src = clean_text.split(":", 1)[1].strip()
        elif clean_text.startswith("Dst Host  :"):
            self.ryu_parsed_dst = clean_text.split(":", 1)[1].strip()
        elif "🚨 ATTACK DETECTED" in text:
            if self.ryu_parsed_src and self.ryu_parsed_dst:
                if self.ryu_parsed_src.startswith("h") and self.ryu_parsed_dst.startswith("h"):
                    self.topo_view.animate_traffic(self.ryu_parsed_src, self.ryu_parsed_dst, is_attack=True)
            if self.ryu_parsed_switch:
                self.topo_view.animate_controller_interaction(self.ryu_parsed_switch)
        elif "✅ Normal Traffic" in text:
            if self.ryu_parsed_src and self.ryu_parsed_dst:
                if self.ryu_parsed_src.startswith("h") and self.ryu_parsed_dst.startswith("h"):
                    self.topo_view.animate_traffic(self.ryu_parsed_src, self.ryu_parsed_dst, is_attack=False)
            if self.ryu_parsed_switch:
                self.topo_view.animate_controller_interaction(self.ryu_parsed_switch)
            
        self.ryu_text.append(text.strip('\n'))
        bar = self.ryu_text.verticalScrollBar()
        bar.setValue(bar.maximum())

    @pyqtSlot(str)
    def log_ryu_error(self, text):
        lower_text = text.lower()
        if "packet in" in lower_text or "eventofppacketin" in lower_text:
            return
            
        self.ryu_text.append(f"<span style='color:red;'>{text.strip()}</span>")
        bar = self.ryu_text.verticalScrollBar()
        bar.setValue(bar.maximum())

    @pyqtSlot(str)
    def log_mininet(self, text):
        self.mininet_text.append(text.strip('\n'))
        bar = self.mininet_text.verticalScrollBar()
        bar.setValue(bar.maximum())

    @pyqtSlot(str)
    def log_mininet_error(self, text):
        self.mininet_text.append(f"<span style='color:red;'>{text.strip()}</span>")
        bar = self.mininet_text.verticalScrollBar()
        bar.setValue(bar.maximum())

    def closeEvent(self, event):
        if self.tester_worker:
            self.tester_worker.stop()
        self.stop_ryu()
        self.stop_mininet()
        # Mininet kalıntılarını temizle
        os.system("sudo mn -c")
        event.accept()

    # ---------------- Automated Testing ----------------
    def start_test_all(self):
        if not self.mininet_worker or not self.mininet_worker.isRunning():
            QMessageBox.warning(self, "Hata", "Test için önce Mininet'i başlatmalısınız!")
            return
            
        if self.ryu_worker and self.ryu_worker.isRunning():
            self.stop_ryu() # Ensure Ryu is stopped before test
            
        # UI updates
        self.test_mode = True
        self.all_test_results = {}
        self.btn_test_all.setEnabled(False)
        self.btn_ryu.setEnabled(False)
        self.btn_mininet.setEnabled(False)
        self.btn_ping.setEnabled(False)
        self.btn_iperf.setEnabled(False)
        self.model_combo.setEnabled(False)

        self.mininet_text.clear()
        self.ryu_text.clear()
        
        models = self.model_manager.get_available_models()
        self.tester_worker = ModelTesterWorker(models)
        
        # Connect signals
        self.tester_worker.start_ryu_signal.connect(self.test_start_ryu_slot)
        self.tester_worker.stop_ryu_signal.connect(self.stop_ryu)
        self.tester_worker.send_cmd_signal.connect(self.test_send_cmd_slot)
        self.tester_worker.set_test_type_signal.connect(self.test_set_type_slot)
        self.tester_worker.change_hosts_signal.connect(self.test_change_hosts_slot)
        self.tester_worker.log_signal.connect(self.log_mininet) # Print test orchestrator logs to mininet terminal for visibility
        self.tester_worker.finished_signal.connect(self.test_finished_slot)
        
        self.tester_worker.start()
        
    @pyqtSlot(str)
    def test_start_ryu_slot(self, model):
        # Set combo box to show which model is running
        idx = self.model_combo.findText(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.start_ryu()

    @pyqtSlot(str, str)
    def test_change_hosts_slot(self, src, dst):
        self.src_combo.blockSignals(True)
        self.dst_combo.blockSignals(True)
        self.src_combo.setCurrentText(src)
        self.dst_combo.setCurrentText(dst)
        self.src_combo.blockSignals(False)
        self.dst_combo.blockSignals(False)
        self.update_node_highlighting()

    @pyqtSlot(str)
    def test_send_cmd_slot(self, cmd):
        if self.mininet_worker and self.mininet_worker.isRunning():
            self.mininet_worker.send_command(cmd)

    @pyqtSlot(str)
    def test_set_type_slot(self, test_type):
        if self.current_test_type != "none" and test_type == "none":
            current_model = self.model_combo.currentText()
            n_total   = self.test_stats["normal"]["total"]
            n_correct = self.test_stats["normal"]["correct"]
            a_total   = self.test_stats["attack"]["total"]
            a_correct = self.test_stats["attack"]["correct"]

            # Confusion matrix values
            TP = self.test_stats["attack"]["tp"]
            TN = self.test_stats["normal"]["tn"]
            FP = self.test_stats["normal"]["fp"]
            FN = self.test_stats["attack"]["fn"]

            n_acc = (n_correct / n_total * 100) if n_total > 0 else 0
            a_acc = (a_correct / a_total * 100) if a_total > 0 else 0
            o_total   = n_total + a_total
            o_correct = n_correct + a_correct
            o_acc = (o_correct / o_total * 100) if o_total > 0 else 0

            precision = (TP / (TP + FP) * 100) if (TP + FP) > 0 else 0
            recall    = (TP / (TP + FN) * 100) if (TP + FN) > 0 else 0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
            fpr = (FP / (FP + TN) * 100) if (FP + TN) > 0 else 0  # False Positive Rate
            fnr = (FN / (FN + TP) * 100) if (FN + TP) > 0 else 0  # False Negative Rate (Miss Rate)

            self.all_test_results[current_model] = {
                "normal_acc": n_acc,
                "attack_acc": a_acc,
                "overall_acc": o_acc,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "fpr": fpr,
                "fnr": fnr,
                "TP": TP,
                "TN": TN,
                "FP": FP,
                "FN": FN,
                "n_total": n_total,
                "a_total": a_total,
            }

        self.current_test_type = test_type
        if test_type == "normal":
            self.test_stats = {
                "normal": {"total": 0, "correct": 0, "tn": 0, "fp": 0},
                "attack": {"total": 0, "correct": 0, "tp": 0, "fn": 0}
            }

    @pyqtSlot()
    def test_finished_slot(self):
        self.test_mode = False
        self.current_test_type = "none"
        
        self.btn_test_all.setEnabled(True)
        self.btn_ryu.setEnabled(True)
        self.btn_mininet.setEnabled(True)
        self.btn_ping.setEnabled(True)
        self.btn_iperf.setEnabled(True)
        self.model_combo.setEnabled(True)
        
        self.log_mininet("\n🎉 TÜM TESTLER TAMAMLANDI!")
        self.show_results_dialog()

    def show_results_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Test Sonuçları")
        dialog.setMinimumSize(1000, 850)  # Responsive base size
        
        # Make the dialog itself resizable with layouts
        layout = QVBoxLayout(dialog)
        dialog.setLayout(layout)

        dialog.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QTabWidget { background-color: #0f172a; }
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 6px;
                background: #1e293b;
            }
            QTabBar::tab {
                background: #0f172a;
                color: #94a3b8;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                min-width: 120px;
            }
            QTabBar::tab:selected { background: #3b82f6; color: white; }
            QTabBar::tab:hover:!selected { background: #1e293b; color: #e2e8f0; }
        """)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(14)

        title_label = QLabel("Model Performans Analizi")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3b82f6; padding-bottom: 4px;")
        title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        outer_layout.addWidget(title_label)

        tabs = QTabWidget()
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer_layout.addWidget(tabs)

        # ---- Prepare data ----
        models = list(self.all_test_results.keys())
        short_models = [m.replace('.pkl','').replace('.joblib','') for m in models]
        res_list     = [self.all_test_results[m] for m in models]

        # Helper to safely get metric
        def g(res, key, default=0):
            return res.get(key, default)

        normal_accs  = [g(r,'normal_acc')  for r in res_list]
        attack_accs  = [g(r,'attack_acc')  for r in res_list]
        overall_accs = [g(r,'overall_acc') for r in res_list]
        precisions   = [g(r,'precision')   for r in res_list]
        recalls      = [g(r,'recall')      for r in res_list]
        f1s          = [g(r,'f1')          for r in res_list]
        fprs         = [g(r,'fpr')         for r in res_list]
        fnrs         = [g(r,'fnr')         for r in res_list]

        DARK_BG  = '#0f172a'
        PANEL_BG = '#1e293b'
        C_TEXT   = '#e2e8f0'
        C_GRID   = '#334155'
        C_PREC   = '#8b5cf6'
        C_REC    = '#ec4899'
        C_F1     = '#06b6d4'
        C_FP     = '#f59e0b'
        C_FN     = '#ef4444'

        def styled_fig(nrows=1, ncols=1):
            fig = Figure(facecolor=DARK_BG)
            axes = []
            for i in range(nrows * ncols):
                ax = fig.add_subplot(nrows, ncols, i+1, facecolor=PANEL_BG)
                ax.tick_params(colors=C_TEXT, labelsize=9)
                ax.xaxis.label.set_color(C_TEXT)
                ax.yaxis.label.set_color(C_TEXT)
                ax.title.set_color(C_TEXT)
                for spine in ['bottom','left']:
                    ax.spines[spine].set_color(C_GRID)
                for spine in ['top','right']:
                    ax.spines[spine].set_visible(False)
                ax.grid(axis='y', color=C_GRID, linestyle='--', linewidth=0.6, alpha=0.6)
                axes.append(ax)
            return fig, (axes[0] if len(axes)==1 else axes)

        def annotate(ax, rects, fmt='{:.1f}', color=C_TEXT, fontsize=7.5):
            for rect in rects:
                h = rect.get_height()
                ax.annotate(fmt.format(h),
                            xy=(rect.get_x() + rect.get_width()/2, h),
                            xytext=(0, 3), textcoords='offset points',
                            ha='center', va='bottom', fontsize=fontsize, color=color)

        x = np.arange(len(short_models))

        # =========================================
        # TAB 1 – Detaylı Sonuç Tablosu
        # =========================================
        tab_table = QWidget()
        tab_table.setStyleSheet("background-color: #0f172a;")
        t_layout = QVBoxLayout(tab_table)
        t_layout.setContentsMargins(12, 12, 12, 12)

        cols = ["Model", "Doğruluk (%)", "Atak Tespiti (%)", "Genel (%)",
                "Duyarlılık/Recall (%)", "F1 (%)",
                "Yanlış Alarm %", "Kaçan Atak %"]
        table = QTableWidget()
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.verticalHeader().setVisible(False)
        table.setFocusPolicy(Qt.NoFocus)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setShowGrid(True)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Responsive Table
        
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch) # Responsive stretch for model name
        for ci in range(1, len(cols)):
            hdr.setSectionResizeMode(ci, QHeaderView.ResizeToContents)
        hdr.setDefaultAlignment(Qt.AlignCenter)
        table.setRowCount(len(models))

        for ri, (model, res) in enumerate(self.all_test_results.items()):
            values = [
                model,
                f"{g(res,'normal_acc'):.2f}%",
                f"{g(res,'attack_acc'):.2f}%",
                f"{g(res,'overall_acc'):.2f}%",
                f"{g(res,'recall'):.2f}%",
                f"{g(res,'f1'):.2f}%",
                f"{g(res,'fpr'):.2f}%",
                f"{g(res,'fnr'):.2f}%",
            ]
            for ci, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter if ci > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(ri, ci, item)

        t_layout.addWidget(table)
        tabs.addTab(tab_table, "📊 Detaylı Tablo")

        # =========================================
        # TAB 2 – Precision / Recall / F1 Bar
        # =========================================
        tab_prf = QWidget()
        tab_prf.setStyleSheet("background-color: #0f172a;")
        prf_layout = QVBoxLayout(tab_prf)
        prf_layout.setContentsMargins(8, 8, 8, 8)

        fig_prf, ax_prf = styled_fig()
        w = 0.26
        rp = ax_prf.bar(x - w, precisions, w, label='Hassasiyet', color=C_PREC, alpha=0.88, zorder=3)
        rr = ax_prf.bar(x,     recalls,    w, label='Recall',     color=C_REC,  alpha=0.88, zorder=3)
        rf = ax_prf.bar(x + w, f1s,        w, label='F1 Skoru',   color=C_F1,   alpha=0.88, zorder=3)
        annotate(ax_prf, rp); annotate(ax_prf, rr); annotate(ax_prf, rf)
        ax_prf.set_xticks(x)
        ax_prf.set_xticklabels(short_models, rotation=15, ha='right', fontsize=9)
        ax_prf.set_ylim(0, 115)
        ax_prf.set_ylabel('Oran (%)', color=C_TEXT)
        ax_prf.set_title('Hassasiyet / Recall / F1 Karşılaştırması', fontsize=11, color=C_TEXT, pad=10)
        ax_prf.legend(facecolor=PANEL_BG, labelcolor=C_TEXT, edgecolor=C_GRID, fontsize=9)
        fig_prf.tight_layout()

        canvas_prf = FigureCanvas(fig_prf)
        canvas_prf.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        prf_layout.addWidget(canvas_prf)
        tabs.addTab(tab_prf, "📈 Precision/Recall/F1")

        # =========================================
        # TAB 3 – Konfüzyon Matrisleri (Ayrı Ayrı)
        # =========================================
        tab_conf = QWidget()
        tab_conf.setStyleSheet("background-color: #0f172a;")
        conf_layout = QVBoxLayout(tab_conf)
        conf_layout.setContentsMargins(8, 8, 8, 8)

        n_models = len(models)
        ncols = min(3, max(1, n_models))
        nrows = (n_models + ncols - 1) // ncols
        
        fig_conf, axes = styled_fig(nrows, ncols)
        if not isinstance(axes, list) and not isinstance(axes, np.ndarray):
            axes = [axes]
        elif isinstance(axes, np.ndarray):
            axes = axes.flatten()
            
        for idx, (model, res) in enumerate(self.all_test_results.items()):
            if idx < len(axes):
                ax = axes[idx]
                tp = int(g(res, 'TP'))
                tn = int(g(res, 'TN'))
                fp = int(g(res, 'FP'))
                fn = int(g(res, 'FN'))
                cm_data = np.array([[tn, fp], [fn, tp]])
                
                cax = ax.imshow(cm_data, cmap='Blues', aspect='auto')
                thresh = cm_data.max() / 2.
                for i in range(2):
                    for j in range(2):
                        val = cm_data[i, j]
                        color = 'white' if val > thresh else 'black'
                        ax.text(j, i, str(int(val)), ha='center', va='center', color=color, fontweight='bold')
                
                ax.set_title(short_models[idx], pad=15, color=C_TEXT, fontsize=10)
                ax.set_xticks([0, 1])
                ax.set_yticks([0, 1])
                ax.set_xticklabels(['Normal', 'Atak'], color=C_TEXT)
                ax.set_yticklabels(['Normal', 'Atak'], color=C_TEXT, rotation=90, va='center')
                ax.set_xlabel('Tahmin Edilen Sınıf', color=C_TEXT, fontsize=9)
                if idx % ncols == 0:
                    ax.set_ylabel('Gerçek Sınıf', color=C_TEXT, fontsize=9)
                
                ax.grid(False)

        for idx in range(n_models, len(axes)):
            axes[idx].set_visible(False)

        fig_conf.tight_layout()

        canvas_conf = FigureCanvas(fig_conf)
        canvas_conf.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        conf_layout.addWidget(canvas_conf)
        tabs.addTab(tab_conf, "🔢 Konfüzyon Matrisleri")

        # =========================================
        # TAB 4 – False Alarm & Miss Rate
        # =========================================
        tab_err = QWidget()
        tab_err.setStyleSheet("background-color: #0f172a;")
        err_layout = QVBoxLayout(tab_err)
        err_layout.setContentsMargins(8, 8, 8, 8)

        fig_err, ax_err = styled_fig()
        w3 = 0.35
        re1 = ax_err.bar(x - w3/2, fprs, w3, label='Yanlış Alarm Oranı (FPR)', color=C_FP, alpha=0.88, zorder=3)
        re2 = ax_err.bar(x + w3/2, fnrs, w3, label='Kaçan Atak Oranı (FNR)',   color=C_FN, alpha=0.88, zorder=3)
        annotate(ax_err, re1, fmt='{:.1f}%'); annotate(ax_err, re2, fmt='{:.1f}%')
        ax_err.set_xticks(x)
        ax_err.set_xticklabels(short_models, rotation=15, ha='right', fontsize=9)
        ax_err.set_ylim(0, max(max(fprs+[1]), max(fnrs+[1])) * 1.4)
        ax_err.set_ylabel('Oran (%)', color=C_TEXT)
        ax_err.set_title('Hata Oranları: Yanlış Alarm (FPR) ve Kaçan Atak (FNR)', fontsize=11, color=C_TEXT, pad=10)
        ax_err.legend(facecolor=PANEL_BG, labelcolor=C_TEXT, edgecolor=C_GRID, fontsize=9)
        fig_err.tight_layout()

        canvas_err = FigureCanvas(fig_err)
        canvas_err.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        err_layout.addWidget(canvas_err)
        tabs.addTab(tab_err, "⚠️ Hata Oranları")

        # ---- Close / Save Buttons ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        def save_as_png():
            file_path, _ = QFileDialog.getSaveFileName(
                dialog, "Sonuçları PNG Olarak Kaydet", "test_sonuclari.png", "PNG Dosyaları (*.png)"
            )
            if file_path:
                # Grab the dialog window to save it as an image
                pixmap = dialog.grab()
                if pixmap.save(file_path, "PNG"):
                    QMessageBox.information(dialog, "Başarılı", f"Test sonuçları başarıyla kaydedildi:\n{file_path}")
                else:
                    QMessageBox.warning(dialog, "Hata", "Görsel kaydedilirken bir hata oluştu!")

        save_btn = QPushButton("Sonuçları Kaydet (PNG)")
        save_btn.clicked.connect(save_as_png)
        save_btn.setStyleSheet(STYLE_BTN_SUCCESS)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        btn_layout.addWidget(save_btn)

        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(dialog.accept)
        close_btn.setStyleSheet(STYLE_BTN_PRIMARY)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        btn_layout.addWidget(close_btn)
        
        outer_layout.addLayout(btn_layout)
        layout.addLayout(outer_layout)

        dialog.exec_()



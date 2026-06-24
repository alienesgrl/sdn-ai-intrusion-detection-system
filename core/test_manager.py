import time
import random
from PyQt5.QtCore import QThread, pyqtSignal

class ModelTesterWorker(QThread):
    start_ryu_signal = pyqtSignal(str)
    stop_ryu_signal = pyqtSignal()
    send_cmd_signal = pyqtSignal(str)
    set_test_type_signal = pyqtSignal(str)
    change_hosts_signal = pyqtSignal(str, str)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, models):
        super().__init__()
        self.models = models
        self._is_running = True

    def run(self):
        try:
            # Randomly pick source and destination hosts once for the entire test run (from h1 to h21)
            all_hosts = [f"h{i}" for i in range(1, 22)]
            src, dst = random.sample(all_hosts, 2)
            
            self.change_hosts_signal.emit(src, dst)

            for model in self.models:
                if not self._is_running:
                    break
                
                self.log_signal.emit(f"\n======================================")
                self.log_signal.emit(f"🚀 TEST BAŞLIYOR: {model} ({src} -> {dst})")
                self.log_signal.emit(f"======================================")

                # 1. Start Ryu with specific model
                self.start_ryu_signal.emit(model)
                
                # Wait for Ryu and model to load
                self.log_signal.emit("⏳ Modelin yüklenmesi bekleniyor (10sn)...")
                self.sleep_safe(10)
                if not self._is_running: break

                # 2. Normal Traffic Test (Ping)
                self.set_test_type_signal.emit("normal")
                self.log_signal.emit(f"🟢 Normal trafik testi başlatılıyor (Ping {src} -> {dst})...")
                # Send 10 pings, will take about 10 seconds
                self.send_cmd_signal.emit(f"{src} ping -c 10 {dst} &")
                self.sleep_safe(12)
                if not self._is_running: break

                # 3. Attack Traffic Test (Iperf)
                self.set_test_type_signal.emit("attack")
                self.log_signal.emit(f"🔴 Atak trafik testi başlatılıyor (Iperf UDP Flood {src} -> {dst})...")
                # Start iperf server on dst
                self.send_cmd_signal.emit(f"{dst} iperf -u -s -p 5001 &")
                self.sleep_safe(1)
                # Start iperf client on src (UDP attack for 10 seconds)
                self.send_cmd_signal.emit(f"{src} iperf -u -c {dst} -b 100M -t 10 &")
                self.sleep_safe(12)
                if not self._is_running: break
                
                # Clean up iperf processes
                self.send_cmd_signal.emit("sh pkill -9 iperf")

                # 4. Stop Ryu and calculate stats for this model
                self.stop_ryu_signal.emit()
                self.set_test_type_signal.emit("none")
                self.log_signal.emit(f"✅ {model} testi tamamlandı. Ryu durduruluyor...")
                self.sleep_safe(3)

        except Exception as e:
            self.log_signal.emit(f"❌ Test sırasında hata: {e}")
        finally:
            self.finished_signal.emit()

    def sleep_safe(self, seconds):
        """Sleeps in small chunks to allow quick cancellation."""
        for _ in range(seconds * 10):
            if not self._is_running:
                break
            time.sleep(0.1)

    def stop(self):
        self._is_running = False

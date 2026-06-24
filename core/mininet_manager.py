import subprocess
import threading
import sys
from PyQt5.QtCore import QThread, pyqtSignal
import signal

class MininetWorker(QThread):
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None
        self._is_running = True

    def run(self):
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Arka planda stderr okumak için
            def read_stderr():
                for line in self.process.stderr:
                    if not self._is_running: break
                    self.error_signal.emit(line)

            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()

            # Ana thread'de stdout okumak
            for line in self.process.stdout:
                if not self._is_running: break
                self.output_signal.emit(line)

            self.process.wait()
        except Exception as e:
            self.error_signal.emit(f"Mininet başlatılırken hata oluştu: {str(e)}\n")
        finally:
            self.finished_signal.emit()

    def send_command(self, cmd):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
                self.output_signal.emit(f"Mininet> {cmd}\n")
            except Exception as e:
                self.error_signal.emit(f"Komut gönderimi başarısız: {str(e)}\n")



    def stop(self):
        self._is_running = False

        if self.process and self.process.poll() is None:
            # 1. Graceful exit mininet CLI
            try:
                self.process.stdin.write("exit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=3)
            except Exception:
                pass

            # 2. Try to terminate
            if self.process.poll() is None:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2)
                except Exception:
                    pass

            # 3. Force kill if still running
            if self.process.poll() is None:
                try:
                    if "sudo" in self.command:
                        subprocess.run(["sudo", "pkill", "-9", "-f", "topo/topo.py"], stderr=subprocess.DEVNULL)
                    self.process.kill()
                    self.process.wait(timeout=1)
                except Exception as e:
                    self.error_signal.emit(f"Kill başarısız: {e}\n")

        # ✅ Mininet cleanup (mn -c)
        try:
            if "sudo" in self.command:
                subprocess.run(["sudo", "mn", "-c"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["mn", "-c"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print("Mininet cleanup hatası:", e)
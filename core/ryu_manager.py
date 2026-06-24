import subprocess
import threading
import os
from PyQt5.QtCore import QThread, pyqtSignal

class RyuWorker(QThread):
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, command, env_kwargs=None):
        super().__init__()
        self.command = command
        self.env_kwargs = env_kwargs if env_kwargs else {}
        self.process = None
        self._is_running = True

    def run(self):
        try:
            # Sistemdeki ortam değişkenlerini alıp, üzerine controller için gerekenleri ekliyoruz
            run_env = os.environ.copy()
            run_env.update(self.env_kwargs)
            run_env["PYTHONUNBUFFERED"] = "1"

            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=run_env
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
            self.error_signal.emit(f"Ryu başlatılırken hata oluştu: {str(e)}\n")
        finally:
            self.finished_signal.emit()

    def stop(self):
        self._is_running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except:
                self.process.kill()

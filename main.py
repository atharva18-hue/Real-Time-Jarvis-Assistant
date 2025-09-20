# main.py — Real-Time Jarvis Assistant (Fullscreen + Voice + Commands)

import sys
import webbrowser
import datetime
import random
import wikipedia
import subprocess
import os

from PyQt5 import QtCore, QtWidgets
import speech_recognition as sr
import pyttsx3

# ------------------ TTS Helper ------------------
class TTSWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    speaking = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = pyttsx3.init()
        self._engine.setProperty('rate', 200)
        self._engine.setProperty('volume', 1.0)
        self._queue = []
        self._running = False
        self._lock = QtCore.QMutex()

    @QtCore.pyqtSlot(str)
    def say(self, text):
        self._lock.lock()
        self._queue.append(text)
        self._lock.unlock()
        if not self._running:
            QtCore.QTimer.singleShot(0, self._process_queue)

    def _process_queue(self):
        self._running = True
        while True:
            self._lock.lock()
            if not self._queue:
                self._lock.unlock()
                break
            text = self._queue.pop(0)
            self._lock.unlock()
            self.speaking.emit(text)
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                self._engine.stop()
            except Exception as e:
                print("TTS error:", e)
            QtCore.QThread.msleep(100)
        self._running = False
        self.finished.emit()

# ------------------ Speech Recognition Worker ------------------
class ListenerWorker(QtCore.QThread):
    heard = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._recognizer = sr.Recognizer()

    def run(self):
        try:
            with sr.Microphone() as source:
                self._running = True
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
                while self._running:
                    audio = self._recognizer.listen(source, phrase_time_limit=6)
                    try:
                        text = self._recognizer.recognize_google(audio)
                        self.heard.emit(text)
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._running = False

# ------------------ Main Window ------------------
class JarvisWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("REAL-TIME JARVIS ASSISTANT")
        self.showFullScreen()
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background-color: #0a0f1c;")
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(50, 30, 50, 30)
        main_layout.setSpacing(20)

        # Title
        self.title_label = QtWidgets.QLabel("R E A L - T I M E   J A R V I S")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setStyleSheet(
            "color: #00f0ff; font-size:50px; font-weight:900; letter-spacing:6px;"
        )
        main_layout.addWidget(self.title_label)

        # Panels
        panels_layout = QtWidgets.QHBoxLayout()
        panels_layout.setSpacing(40)
        main_layout.addLayout(panels_layout)

        # ---------------- Left Panel ----------------
        left = QtWidgets.QFrame()
        left.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #071024, stop:1 #03101a); border-radius:15px;"
        )
        left.setMinimumWidth(550)
        left.setMaximumWidth(550)
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setAlignment(QtCore.Qt.AlignCenter)
        left_layout.setSpacing(25)

        # Mic Circle
        self.circle = QtWidgets.QLabel()
        self.circle.setFixedSize(250, 250)
        self.circle_state = "idle"
        self.circle.setStyleSheet(self.circle_css(0, "#0d3140"))
        left_layout.addWidget(self.circle)

        # Start/Stop Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("🎙️ Start")
        self.start_btn.setFixedSize(160, 60)
        self.start_btn.clicked.connect(self.start_listening)
        self.start_btn.setStyleSheet(
            "background: rgba(0,255,200,0.3); font-size:20px; border-radius:10px;"
        )
        self.stop_btn = QtWidgets.QPushButton("🛑 Stop")
        self.stop_btn.setFixedSize(160, 60)
        self.stop_btn.clicked.connect(self.stop_listening)
        self.stop_btn.setStyleSheet(
            "background: rgba(255,50,50,0.3); font-size:20px; border-radius:10px;"
        )
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        left_layout.addLayout(btn_layout)

        # Status
        self.status_label = QtWidgets.QLabel("Status: Idle")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #9fb3bd; font-size:16px;")
        left_layout.addWidget(self.status_label)
        panels_layout.addWidget(left)

        # ---------------- Right Panel ----------------
        right = QtWidgets.QFrame()
        right.setStyleSheet("background: #071021; border-radius:15px;")
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setSpacing(15)

        # Conversation Log
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(
            "background:#02101a; color:#c6ffff; font-size:24px; border-radius:6px; padding:10px;"
        )
        self.log.setPlaceholderText("Conversation log...")
        right_layout.addWidget(self.log)

        exit_btn = QtWidgets.QPushButton("Exit")
        exit_btn.setFixedHeight(40)
        exit_btn.clicked.connect(self.close)
        right_layout.addWidget(exit_btn)
        panels_layout.addWidget(right)

        # ---------------- TTS ----------------
        self.tts_thread = QtCore.QThread()
        self.tts_worker = TTSWorker()
        self.tts_worker.moveToThread(self.tts_thread)
        self.tts_thread.start()

        # ---------------- Pulse Animation ----------------
        self.pulse_timer = QtCore.QTimer()
        self.pulse_timer.timeout.connect(self.animate_circle)
        self.pulse_value = 0
        self.pulse_dir = 1
        self.pulse_timer.start()

        # Listener
        self.listener = None
        self.listening = False

        # Auto Welcome
        QtCore.QTimer.singleShot(
            800, lambda: self.say("Hello Sir, I am Jarvis. What do you want me to do, Sir?")
        )

    # Circle Animation
    def circle_css(self, intensity, color):
        return f"border-radius:125px; background: qradialgradient(cx:0.3, cy:0.3, radius:1, fx:0.3, fy:0.3, stop:0 rgba(0,240,255,0.06), stop:1 rgba(0,0,0,0));"

    def animate_circle(self):
        if self.circle_state == "idle":
            step, color = 1, "#08323a"
        elif self.circle_state == "listening":
            step, color = 3, "#00e5ff"
        else:
            step, color = 5, "#7fffd4"
        self.pulse_value += self.pulse_dir * step
        if self.pulse_value > 9: self.pulse_dir = -1
        if self.pulse_value < 0: self.pulse_dir = 1
        self.circle.setStyleSheet(self.circle_css(max(0, min(10, int(self.pulse_value))), color))

    # Logging & TTS
    def log_msg(self, who, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        color = "#7ef3a6" if who == "You" else "#7ef3ff"
        self.log.append(f"<span style='color:#9aa7b0'>[{ts}]</span> <b style='color:{color}'>{who}:</b> {text}")
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def say(self, text):
        QtCore.QMetaObject.invokeMethod(self.tts_worker, "say", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, text))
        self.log_msg("Jarvis", text)
        self.circle_state = "speaking"

    # Start/Stop
    def start_listening(self):
        if not self.listening:
            self.listener = ListenerWorker()
            self.listener.heard.connect(self.on_heard)
            self.listener.error.connect(self.on_error)
            self.listener.start()
            self.listening = True
            self.status_label.setText("Status: Listening")
            self.circle_state = "listening"

    def stop_listening(self):
        if self.listening and self.listener:
            self.listener.stop()
            self.listener.wait(1000)
            self.listener = None
            self.listening = False
            self.status_label.setText("Status: Idle")
            self.circle_state = "idle"

    # Speech Handling
    def on_heard(self, text):
        self.log_msg("You", text)
        self.process_command(text)

    def on_error(self, err):
        self.say("There was an error with speech recognition.")

    # Commands (Voice + Foreground Open)
    def process_command(self, c):
        c = c.lower().strip()
        try:
            if "youtube" in c:
                self.say("Opening YouTube Sir")
                subprocess.Popen("start chrome https://www.youtube.com", shell=True)
            elif "google" in c:
                self.say("Opening Google Sir")
                subprocess.Popen("start chrome https://www.google.com", shell=True)
            elif "gmail" in c:
                self.say("Opening Gmail Sir")
                subprocess.Popen("start chrome https://mail.google.com", shell=True)
            elif "chrome" in c:
                self.say("Opening Chrome Sir")
                subprocess.Popen("start chrome", shell=True)
            elif "notepad" in c:
                self.say("Opening Notepad Sir")
                subprocess.Popen("notepad")
            elif "calculator" in c:
                self.say("Opening Calculator Sir")
                subprocess.Popen("calc.exe")
            elif "paint" in c:
                self.say("Opening Paint Sir")
                subprocess.Popen("mspaint")
            elif "spotify" in c:
                self.say("Opening Spotify Sir")
                spotify_path = f"C:/Users/{os.getlogin()}/AppData/Roaming/Spotify/Spotify.exe"
                if os.path.exists(spotify_path):
                    subprocess.Popen([spotify_path])
                else:
                    subprocess.Popen("start chrome https://open.spotify.com", shell=True)
            elif "camera" in c:
                self.say("Opening Camera Sir")
                subprocess.Popen("start microsoft.windows.camera:", shell=True)
            elif "pdf" in c:
                self.say("Opening PDF Reader Sir")
                subprocess.Popen("start acrord32", shell=True)
            elif "sticky notes" in c:
                self.say("Opening Sticky Notes Sir")
                subprocess.Popen("StikyNot.exe")
            elif "time" in c:
                t = datetime.datetime.now().strftime("%H:%M:%S")
                self.say(f"The time is {t} Sir")
            elif "date" in c:
                d = datetime.datetime.now().strftime("%d-%m-%Y")
                self.say(f"Today's date is {d} Sir")
            elif "joke" in c:
                jokes = [
                    "Why don't scientists trust atoms? Because they make up everything!",
                    "I told my computer I needed a break, it said it needed one too!",
                    "Why did the math book look sad? Because it had too many problems."
                ]
                self.say(random.choice(jokes))
            elif "exit" in c or "quit" in c:
                self.say("Goodbye Sir, shutting down.")
                QtCore.QTimer.singleShot(1200, self.close)
            else:
                self.say("Sorry Sir, I don't recognize this command.")
        except Exception as e:
            self.say("Error executing command.")

    def split_text(self, text, n):
        parts, cur = [], ""
        for sentence in text.replace("\n", " ").split(". "):
            if len(cur) + len(sentence) + 2 <= n:
                cur += (". " if cur else "") + sentence
            else:
                if cur: parts.append(cur.strip())
                cur = sentence
        if cur: parts.append(cur.strip())
        return parts

# ------------------ Run ------------------
if __name__ == "__main__":
    try:
        app = QtWidgets.QApplication(sys.argv)
        win = JarvisWindow()
        win.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("Error:", e)



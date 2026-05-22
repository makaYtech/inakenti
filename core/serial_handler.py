import serial
import time
from config.settings import (
    PORT, BAUD, HANDSHAKE_TIMEOUT, PING_INTERVAL,
    PONG_TIMEOUT, MAX_MISSED_PONGS
)

class SerialHandler:
    def __init__(self):
        self.ser = None
        self.last_ping = 0.0
        self.last_pong = 0.0

    def is_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open

    def connect(self) -> bool:
        """Попытаться установить соединение с рукопожатием."""
        try:
            s = serial.Serial(PORT, BAUD, timeout=0.1)
            print("Port is open")
            time.sleep(0.5)
            if self._do_handshake(s):
                print("Handshake OK")
                self.ser = s
                self.last_pong = time.time()
                self.last_ping = time.time()
                return True
            else:
                print("Handshake Failed")
                s.close()
        except serial.SerialException:
            pass
        return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b"EXIT\n")
                self.ser.flush()
            except Exception:
                pass
            self.ser.close()
        self.ser = None

    def write_line(self, msg: str):
        """Безопасно отправить строку на LCD (latin-1)."""
        if not self.ser or not self.ser.is_open:
            return
        try:
            self.ser.write(msg.encode('latin-1'))
        except (serial.SerialException, OSError):
            self.ser = None

    def read_line(self) -> str | None:
        """Прочитать одну строку из сериал-буфера (без блокировки)."""
        if not self.ser or not self.ser.is_open:
            return None
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('latin-1', errors='ignore')
                return line.strip() if line else None
        except (serial.SerialException, OSError):
            self.ser = None
        return None

    def send_keepalive_if_needed(self):
        """Отправить PING, если подошло время."""
        now = time.time()
        if not self.is_connected():
            return
        if now - self.last_ping > PING_INTERVAL:
            try:
                self.ser.write(b"PING\n")
                self.last_ping = now
            except (serial.SerialException, OSError):
                self.ser = None

    def check_keepalive_timeout(self) -> bool:
        """Вернуть True, если пора отключаться по таймауту."""
        if not self.is_connected():
            return False
        return (time.time() - self.last_pong) > (MAX_MISSED_PONGS * PONG_TIMEOUT)

    def update_pong(self):
        """Обновить время последнего PONG (вызывается при любом успешном чтении)."""
        self.last_pong = time.time()

    # --- приватные ---
    def _do_handshake(self, s: serial.Serial) -> bool:
        try:
            s.reset_input_buffer()
            s.reset_output_buffer()
            s.timeout = HANDSHAKE_TIMEOUT

            s.write(b"SYN\n")
            start = time.time()
            while time.time() - start < HANDSHAKE_TIMEOUT:
                line = s.readline().decode('latin-1', errors='ignore')
                if not line:
                    continue
                print(line.strip())
                if "SYN_ACK" in line:
                    s.write(b"ACK\n")
                    return True
        except (serial.SerialException, OSError) as e:
            print(f"Handshake error: {e}")
        return False

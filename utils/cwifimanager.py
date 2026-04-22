# CWIFIMANAGER STA ultra-ligero (ESP8266)
import machine
import network
import socket
import utime
import gc
import config

class CWifiManager:
    def __init__(self):
        self.pin_btn = machine.Pin(config.PIN_BOTON_WIFI, machine.Pin.IN, machine.Pin.PULL_UP)
        self.sta = network.WLAN(network.STA_IF)
        self.sock = None
        self.active = False
        self.start_time = 0
        self.last_ok = 0
        self.btn_was_pressed = False

    def btn_pressed(self):
        if self.pin_btn.value() == 0:
            if not self.btn_was_pressed and not self.active:
                self.btn_was_pressed = True
                self.start_connection()
                return True
        else:
            self.btn_was_pressed = False
        return False

    def start_connection(self):
        print("🔌 Botón WiFi → activando STA Antiempaste")
        gc.collect()
        self.sta.active(False)
        utime.sleep_ms(100)
        self.sta.active(True)
        self.sta.connect("Antiempaste", "antiempaste")
        self.active = True
        self.start_time = utime.ticks_ms()
        self.last_ok = 0
        print("Intentando conectar... (20s timeout)")

    def is_connected(self):
        return self.sta.isconnected()

    def get_ip(self):
        if self.is_connected():
            return self.sta.ifconfig()[0]
        return None

    def start_server(self):
        if self.sock:
            return
        try:
            self.sock = socket.socket()
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', 80))
            self.sock.listen(1)
            self.sock.settimeout(0)
            print("Servidor web en puerto 80")
        except:
            self.sock = None

    def handle_client(self):
        if not self.sock:
            return
        try:
            conn, _ = self.sock.accept()
            self.last_ok = utime.ticks_ms()
            try:
                conn.settimeout(0.2)
                conn.recv(512)
            except:
                pass
            try:
                with open('/html/index.html', 'r') as f:
                    html = f.read()
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n" + html.encode())
            except:
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>Hola soy un Dosificador</h1>")
            conn.close()
        except OSError:
            pass
        except Exception:
            pass

    def stop(self):
        print("🔋 Apagando WiFi")
        if self.sock:
            try: self.sock.close()
            except: pass
            self.sock = None
        self.sta.disconnect()
        self.sta.active(False)
        self.active = False

    def process(self):
        if self.btn_pressed():
            return

        if not self.active:
            return

        now = utime.ticks_ms()
        connected = self.is_connected()

        if connected:
            self.last_ok = now
            if not self.sock:
                self.start_server()
                ip = self.get_ip()
                if ip:
                    print(f"✅ Conectado! IP: {ip} → http://{ip}")
        else:
            # Timeout inicial de 20 segundos
            if utime.ticks_diff(now, self.start_time) > 20000:
                print("⏰ Timeout 20s sin conexión")
                self.stop()
                return

        # Si se perdió la conexión → 10 segundos de gracia
        if self.last_ok > 0 and not connected:
            if utime.ticks_diff(now, self.last_ok) > 10000:
                print("Conexión perdida >10s")
                self.stop()
                return

        self.handle_client()
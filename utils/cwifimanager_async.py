# cwifimanager_async.py
# WiFi AP + servidor HTTP asíncrono (uasyncio) - comportamiento igual al original
import uasyncio as asyncio
import machine
import network
import utime
import config
import ujson

INDEX_PATH = '/html/index.html'
AP_ESSID = "Antiempaste"
AP_PASS = "antiempaste"

class CWifiManager:
    def __init__(self, estado_getter=None):
        # estado_getter: función (sin bloques) que retorna dict para /status
        self.boton_wifi = machine.Pin(config.PIN_BOTON_WIFI, machine.Pin.IN, machine.Pin.PULL_UP)
        self.ap = network.WLAN(network.AP_IF)
        self.ap.active(False)
        self.server = None
        self.wifi_active = False
        self.activation_time = 0
        self.last_client_time = 0
        self.button_pressed = False
        self.estado_getter = estado_getter

    # utilitario
    def _get_num_clients(self):
        if not self.ap.active():
            return 0
        try:
            stations = self.ap.status('stations')
            return len(stations) if isinstance(stations, (list, tuple)) else 0
        except:
            return 0

    # activar AP (no crea server aquí)
    def _activate_ap(self):
        print("\n🔌 Activando WiFi AP 'Antiempaste'...")
        try:
            self.ap.config(essid=AP_ESSID, password=AP_PASS, authmode=network.AUTH_WPA_WPA2_PSK)
            self.ap.active(True)
            ip = self.ap.ifconfig()[0]
            print(f"✅ AP activo - IP: {ip}")
        except Exception as e:
            print("❌ Error activando AP:", e)

    # desactivar AP y servidor
    async def _deactivate(self):
        print("🔋 Apagando WiFi para ahorrar batería...")
        # cerrar server si existe
        if self.server:
            try:
                self.server.close()
                await self.server.wait_closed()
                print("🌐 Servidor detenido")
            except Exception as e:
                print("❌ Error cerrando servidor:", e)
            self.server = None
        try:
            self.ap.active(False)
        except Exception:
            pass
        self.wifi_active = False
        self.activation_time = 0
        self.last_client_time = 0

    # manejadores HTTP
    async def _serve_index(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print("📡 Cliente conectado (index):", addr)
        self.last_client_time = utime.ticks_ms()
        try:
            try:
                await reader.read(512)
            except:
                pass
            try:
                with open(INDEX_PATH, 'rb') as f:
                    data = f.read()
                headers = ( "HTTP/1.1 200 OK\r\n"
                            "Content-Type: text/html; charset=utf-8\r\n"
                            "Content-Length: {}\r\n"
                            "Connection: close\r\n\r\n" ).format(len(data))
                # enviar headers como bytes y luego el body binario
                await writer.awrite(headers.encode('utf-8'))
                await writer.awrite(data)
            
            except OSError:
                body = b"404 - index.html no encontrado Sube /html/index.html" 
                headers = ("HTTP/1.1 404 Not Found\r\nContent-Type: text/html; charset=utf-8\r\n" "Content-Length: {}\r\nConnection: close\r\n\r\n").format(len(body)) 
                await writer.awrite(headers.encode('utf-8')) 
                await writer.awrite(body) 
        except Exception as e: print("⚠️ Error serve_index:", e) 
        finally: 
            try: 
                await writer.aclose() 
            except: 
                pass

    async def _serve_status(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print("📡 Cliente conectado (status):", addr)
        self.last_client_time = utime.ticks_ms()
        try:
            # leer petición
            try:
                await reader.read(512)
            except:
                pass
            if self.estado_getter:
                try:
                    estado = self.estado_getter()
                except Exception as e:
                    estado = {"error": str(e)}
            else:
                estado = {"info": "no estado_getter definido"}
            payload = ujson.dumps(estado)
            resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + payload
            await writer.awrite(resp)
        except Exception as e:
            print("⚠️ Error serve_status:", e)
        finally:
            try:
                await writer.aclose()
            except:
                pass

    async def _http_dispatch(self, reader, writer):
        # lee primeros bytes para decidir ruta
        try:
            head = await reader.read(64)
        except:
            head = b''
        if b'GET /status' in head:
            await self._serve_status(reader, writer)
        else:
            await self._serve_index(reader, writer)

    # iniciar servidor asíncrono
    async def _start_server(self):
        if self.server:
            return
        try:
            self.server = await asyncio.start_server(self._http_dispatch, "0.0.0.0", 80)
            print("🌐 Servidor HTTP iniciado en puerto 80 (sirve /html/index.html)")
        except Exception as e:
            print("❌ Error iniciando servidor async:", e)
            self.server = None

    # tarea principal que corre en uasyncio: chequea botón, controla AP/servidor y auto-off
    async def run(self):
        print("CWifiManager: tarea run iniciada")
        while True:
            # boton (PULL_UP)
            if self.boton_wifi.value() == 0:
                if not self.button_pressed:
                    self.button_pressed = True
                    if not self.wifi_active:
                        # activar AP y servidor
                        self._activate_ap()
                        self.wifi_active = True
                        self.activation_time = utime.ticks_ms()
                        self.last_client_time = 0
                        await self._start_server()
                        print("✅ WiFi activada - servidor arrancado")
                # si sigue presionado no reactivar
            else:
                self.button_pressed = False

            if self.wifi_active:
                now = utime.ticks_ms()
                num_clients = self._get_num_clients()
                if num_clients > 0:
                    self.last_client_time = now

                should_deactivate = False
                if num_clients == 0:
                    if self.last_client_time == 0:
                        # nunca se conectó → timeout 60s
                        if utime.ticks_diff(now, self.activation_time) >= 60000:
                            should_deactivate = True
                    else:
                        # se desconectó → 10s gracia
                        if utime.ticks_diff(now, self.last_client_time) >= 10000:
                            should_deactivate = True

                if should_deactivate:
                    await self._deactivate()

            await asyncio.sleep_ms(200)  # ciclo frecuente para respuesta de botón y control
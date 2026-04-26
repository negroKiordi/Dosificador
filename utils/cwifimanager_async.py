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
            # leer petición ligera
            try:
                await reader.read(512)
            except:
                pass
            # leer archivo
            try:
                with open(INDEX_PATH, 'r') as f:
                    html = f.read()
                resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n" + html
            except OSError:
                resp = ("HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
                        "<h1>404 - index.html no encontrado</h1><p>Sube /html/index.html</p>")
            await writer.awrite(resp)
        except Exception as e:
            print("⚠️ Error serve_index:", e)
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


    def _content_type(self, path):
        if path.endswith('.css'):
            return 'text/css'
        if path.endswith('.js'):
            return 'application/javascript'
        if path.endswith('.html') or path.endswith('.htm'):
            return 'text/html'
        if path.endswith('.json'):
            return 'application/json'
        if path.endswith('.png'):
            return 'image/png'
        if path.endswith('.svg'):
            return 'image/svg+xml'
        return 'text/plain'



    async def _serve_static(self, reader, writer, fs_path):
        addr = None
        try:
            addr = writer.get_extra_info('peername')
        except:
            pass
        print("📡 Servir estático:", fs_path, "->", addr)
        self.last_client_time = utime.ticks_ms()
        try:
            # abrir en modo texto para html/css/js, binario para imágenes; usamos 'rb' y decodificamos según tipo
            ctype = self._content_type(fs_path)
            mode = 'rb'
            with open(fs_path, mode) as f:
                data = f.read()
            if isinstance(data, bytes):
                body = data
            else:
                body = str(data).encode('utf-8')
            header = "HTTP/1.1 200 OK\r\nContent-Type: {}\r\nConnection: close\r\n\r\n".format(ctype)
            try:
                await writer.awrite(header)
                # writer.awrite acepta str; para bytes enviamos chunks
            except:
                # si awrite no acepta, intenta writer.write
                try:
                    writer.write(header.encode('utf-8'))
                except:
                    pass
            # enviar body (bytes)
            try:
                # algunas versiones de writer tienen awrite for str only; intentar write for bytes
                await writer.awrite(body if isinstance(body, str) else body)
            except:
                try:
                    writer.write(body)
                except:
                    pass
        except OSError:
            err = ("HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
                   "<h1>404 - archivo no encontrado</h1>")
            try:
                await writer.awrite(err)
            except:
                try:
                    writer.write(err.encode('utf-8'))
                except:
                    pass
        except Exception as e:
            print("⚠️ Error _serve_static:", e)
        finally:
            try:
                await writer.aclose()
            except:
                pass

    async def _http_dispatch(self, reader, writer):
        # lee primeros bytes para decidir ruta
        try:
            head = await reader.read(128)
        except:
            head = b''
        # decidir ruta simple
        req_line = b''
        if head:
            req_line = head.split(b'\r\n', 1)[0]
        path = '/'
        try:
            parts = req_line.split()
            if len(parts) >= 2:
                path = parts[1].decode()
        except:
            path = '/'
        # Rutas manejadas
        if path == '/' or path == '/index.html':
            await self._serve_static(reader, writer, INDEX_PATH)
            return
        if path.startswith('/static/'):
            # mapear /static/x -> /html/x
            sub = path[len('/static/'):]
            fs = '/html/' + sub
            await self._serve_static(reader, writer, fs)
            return
        if path == '/status':
            await self._serve_status(reader, writer)
            return
        # por defecto intentar servir archivo en /html/<route>
        if path.startswith('/'):
            fs = '/html' + path
            await self._serve_static(reader, writer, fs)
            return
        # fallback: servir index
        await self._serve_static(reader, writer, INDEX_PATH)


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

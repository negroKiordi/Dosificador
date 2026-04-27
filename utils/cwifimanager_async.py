# cwifimanager_async.py
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
    def __init__(self, estado_getter=None, parametros=None):
        self.boton_wifi = machine.Pin(config.PIN_BOTON_WIFI, machine.Pin.IN, machine.Pin.PULL_UP)
        self.ap = None                # lazy: crear solo al activar
        self.server_task = None
        self.wifi_active = False
        self.activation_time = 0
        self.last_client_time = 0
        self.button_pressed = False
        self.estado_getter = estado_getter
        self.parametros = parametros
        # map identificadores -> (get,set,unit,label)
        self._param_map = {
            'carga': ('get_Carga','set_Carga','kg','Carga'),
            'dosis': ('get_DosisDiariaFarmaco','set_DosisDiariaFarmaco','ml/100kg','Dosis'),
            'qbomba': ('get_QBomba','set_QBomba','ml/s','Caudal Bomba'),
            'pulso': ('get_tiempoEncendidoBomba','set_tiempoEncendidoBomba','s','Pulso'),
            'descanso': ('get_tiempoDescansoBomba','set_tiempoDescansoBomba','s','Descanso'),
            'contraccion': ('get_porcentajeContraccionTDAVB','set_porcentajeContraccionTDAVB','%','%Contraccion'),
            'qbebida': ('get_QBebida','set_QBebida','l/min','Caudal Bebida'),
            'aguaconsumo': ('get_aguaConsumidaPor100Kg','set_aguaConsumidaPor100Kg','l/100kg','Consumo agua'),
        }
        # referencia a app de microdot (será seteada por attach)
        self._app = None

    def _get_num_clients(self):
        if not self.ap:
            return 0
        try:
            stations = self.ap.status('stations')
            return len(stations) if isinstance(stations, (list, tuple)) else 0
        except:
            return 0

    def _activate_ap(self):
        print("\n🔌 Activando WiFi AP 'Antiempaste'...")
        try:
            import gc
            gc.collect()
        except:
            pass
        try:
            if self.ap is None:
                self.ap = network.WLAN(network.AP_IF)
            try:
                self.ap.active(False)
            except:
                pass
            self.ap.config(essid=AP_ESSID, password=AP_PASS, authmode=network.AUTH_WPA_WPA2_PSK)
            self.ap.active(True)
            ip = self.ap.ifconfig()[0]
            print("✅ AP activo - IP:", ip)
        except OSError as e:
            print("❌ Error activando AP (OSError):", e)
            # intentar liberar y reintentar una vez
            try:
                import gc
                gc.collect()
            except:
                pass
            try:
                if self.ap is None:
                    self.ap = network.WLAN(network.AP_IF)
                self.ap.config(essid=AP_ESSID, password=AP_PASS, authmode=network.AUTH_WPA_WPA2_PSK)
                self.ap.active(True)
                ip = self.ap.ifconfig()[0]
                print("✅ AP activo - IP:", ip)
            except Exception as e2:
                print("❌ Reintento fallo:", e2)

    async def _deactivate(self):
        print("🔋 Apagando WiFi para ahorrar batería...")
        # cancelar server task si existe
        if self.server_task:
            try:
                self.server_task.cancel()
                await self.server_task
            except:
                pass
            self.server_task = None
            print("🌐 Servidor detenido")
        try:
            if self.ap:
                self.ap.active(False)
                # opcional: liberar referencia
                # self.ap = None
        except:
            pass
        self.wifi_active = False
        self.activation_time = 0
        self.last_client_time = 0

    # import diferido y arrancar microdot en tarea uasyncio
    async def _start_server(self):
        try:
            import gc
            gc.collect()
        except:
            pass
        try:
            # import microdot aquí (debe estar en el sistema de archivos)
            from lib.microdot_asyncio import Microdot, Response, send_file
        except Exception as e:
            print("❌ microdot_asyncio no disponible:", e)
            return
        app = Microdot()
        Response.default_content_type = 'text/html; charset=utf-8'

 

        @app.route('/')
        async def root(req):
            try:
                return await send_file(INDEX_PATH)
            except Exception as e:
                return Response("Index not found: {}".format(e), status=404)

        @app.route('/html/configuracion.html')
        async def conf(req):
            try:
                return await send_file('/html/configuracion.html')
            except Exception as e:
                return Response("Configuracion not found: {}".format(e), status=404)
 
        @app.route('/html/config_item.html')
        async def item(req):
            try:
                return await send_file('/html/config_item.html')
            except Exception as e:
                return Response("Config_item not found: {}".format(e), status=404)


        @app.route('/status')
        async def status(req):
            try:
                if self.estado_getter:
                    try:
                        estado = self.estado_getter()
                    except Exception as e:
                        estado = {"error": str(e)}
                else:
                    estado = {"info": "no estado_getter definido"}
                return Response(ujson.dumps(estado), headers={'Content-Type':'application/json'})
            except Exception as e:
                return Response(ujson.dumps({"error": str(e)}), headers={'Content-Type':'application/json'}, status=500)
 
        @app.route('/api/get_param')
        async def api_get(req):
            q = req.args or {}
            name = q.get('name')
            if not name:
                return Response(ujson.dumps({"error":"missing name"}), headers={'Content-Type':'application/json'}, status=400)
            try:
                info = self._param_map.get(name)
                unit = info[2] if info else None
                val = None
                if self.parametros and info:
                    getter = getattr(self.parametros, info[0], None)
                    if getter:
                        val = getter()
                return Response(ujson.dumps({"name":name,"value":val,"unit":unit}), headers={'Content-Type':'application/json'})
            except Exception as e:
                return Response(ujson.dumps({"error":str(e)}), headers={'Content-Type':'application/json'}, status=500)

        @app.route('/api/set_param')
        async def api_set(req):
            q = req.args or {}
            name = q.get('name')
            raw_value = q.get('value')
            if not name:
                return Response(ujson.dumps({"out":False,"msj":"missing name"}), headers={'Content-Type':'application/json'}, status=400)
            # convertir si posible
            value = None
            if raw_value is not None and raw_value != '':
                try:
                    fv = float(raw_value)
                    if fv.is_integer():
                        value = int(fv)
                    else:
                        value = fv
                except:
                    value = raw_value
            try:
                info = self._param_map.get(name)
                if not info:
                    return Response(ujson.dumps({"out":False,"msj":"param desconocido"}), headers={'Content-Type':'application/json'})
                setter = getattr(self.parametros, info[1], None) if self.parametros else None
                if not setter:
                    return Response(ujson.dumps({"out":False,"msj":"setter no encontrado"}), headers={'Content-Type':'application/json'})
                result = setter(value)
                return Response(ujson.dumps(result), headers={'Content-Type':'application/json'})
            except Exception as e:
                return Response(ujson.dumps({"out":False,"msj":str(e)}), headers={'Content-Type':'application/json'}, status=500)

        # attach reference for handlers if needed
        app._wifi_manager = self
        # guardar app para posible uso externo
        self._app = app
        print("🌐 Iniciando microdot server (run_task)...")
        try:
            # run_task bloquea hasta cancelar; ejecutarlo como tarea
            self.server_task = asyncio.create_task(app.run_task(host="0.0.0.0", port=80))
            await self.server_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print("❌ Error en microdot run_task:", e)
        finally:
            self.server_task = None
            print("🌐 microdot server finalizado")

    async def run(self):
        print("CWifiManager: tarea run iniciada (lazy AP, microdot deferred)")
        while True:
            if self.boton_wifi.value() == 0:
                if not self.button_pressed:
                    self.button_pressed = True
                    if not self.wifi_active:
                        self._activate_ap()
                        self.wifi_active = True
                        self.activation_time = utime.ticks_ms()
                        self.last_client_time = 0
                        # arrancar server (async)
                        asyncio.create_task(self._start_server())
                        print("✅ WiFi activada - servidor arrancado (task)")
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
                        if utime.ticks_diff(now, self.activation_time) >= 60000:
                            should_deactivate = True
                    else:
                        if utime.ticks_diff(now, self.last_client_time) >= 10000:
                            should_deactivate = True

                if should_deactivate:
                    await self._deactivate()

            await asyncio.sleep_ms(200)

# helper para integrar con main
def attach_wifi_manager_to_app(wm):
    # solo asigna la referencia en caso de que microdot app exista en wm._start_server
    wm._app = getattr(wm, '_app', None)
    # también exportar atributo en caso de import externo
    global APP_WIFI_MANAGER
    APP_WIFI_MANAGER = wm

# fin cwifimanager_async.py

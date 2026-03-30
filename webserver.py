# webserver.py

import uasyncio as asyncio
import network
import config
import utils.estado as estado
import utils.errores as errores
import utils.storage as storage
import utils.reloj as reloj
import os
from machine import Timer
import time



wifi_activo = False
servidor_activo = False

wlan = network.WLAN(network.STA_IF)



# Iniciar WiFi STA
async def conectar_wifi():
    global wifi_activo
    global wlan
    
    print(wlan)
    
    if wlan.isconnected():
        print("Desconectando WiFi previa...")
        try:
            wlan.disconnect()
            await asyncio.sleep(1)
        except:
            pass

    wlan.active(False)
    await asyncio.sleep(1)
    wlan.active(True)
    redes = wlan.scan()
    for r in redes:
        print(r[0].decode())   # imprime el SSID
    
    
    print("Conectando a:", config.WIFI_SSID)
    estado.led.on()
    
    try:
        wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
#        wlan.connect(config.WIFI_SSID)
    except OSError as e:
        print("Error al iniciar conexión WiFi:", e)
        wifi_activo = False
        return False

    for _ in range(config.TIEMPO_MAX_WIFI):
        if wlan.isconnected():
            print("WiFi conectada:", wlan.ifconfig())
            wifi_activo = True
            return True
        print("isconnected:", wlan.isconnected(), " status:", wlan.status())
        await asyncio.sleep(1)

    print("No se pudo conectar al WiFi")
    wlan.active(False)
    wifi_activo = False
    return False


# Apagar WiFi
def apagar_wifi():
    global wifi_activo
    global wlan
    wlan.active(False)
    wifi_activo = False
    estado.led.off()

# Cargar HTML
def cargar_html(nombre):
    try:
        with open("/html/" + nombre) as f:
            return f.read()
    except:
        return "Error al cargar HTML"

# Servidor principal
async def servidor_web(boton):
    global servidor_activo
    while True:
        if not wifi_activo and (boton.value() == 0):
            print("Conectar wifi")
            if await conectar_wifi():
                asyncio.create_task(lanzar_servidor())
        await asyncio.sleep(0.5)

# Lanzar servidor HTTP
async def lanzar_servidor():
    global servidor_activo
    servidor_activo = True

    print("Lanzar servidor")
    async def handle(reader, writer):
        global servidor_activo
        try:
            data = await reader.read(1024)
            peticion = data.decode().split("\r\n")[0]
            metodo, ruta, _ = peticion.split()

            if ruta == "/":
                html = cargar_html("index.html")
                html = html.replace("{{AGUA}}", f"{estado.agua.litros():.2f} L")
                html = html.replace("{{REMEDIO}}", f"{estado.remedio.litros():.2f} ml")
                html = html.replace("{{DATETIME}}", str(estado.rtc.datetime()))

                err = errores.get_error()
                leyenda = []
                if err == 0:
                    leyenda.append("Sin errores")
                else:
                    if err & 1:
                        leyenda.append("Error de dosificación")
                    if err & 2:
                        leyenda.append("Memoria llena")
                html = html.replace("{{ERRORES}}", "<br>".join(leyenda))

                respuesta(writer, html)

            elif ruta == "/estado.json":
                err = errores.get_error()
                leyenda = []
                if err == 0:
                    leyenda.append("Sin errores")
                else:
                    if err & 1:
                        leyenda.append("Error de dosificación")
                    if err & 2:
                        leyenda.append("Memoria llena")

                data = {
                    "agua": f"{estado.agua.litros():.2f} L",
                    "remedio": f"{estado.remedio.litros():.2f} ml",
                    "datetime": str(estado.rtc.datetime()),
                    "errores": "<br>".join(leyenda)
                }
                import ujson
                writer.write("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
                writer.write(ujson.dumps(data))


            elif ruta == "/configFechaHora.html":
                respuesta(writer, cargar_html("configFechaHora.html"))


            elif ruta.startswith("/settime"):
                headers, body = data.decode().split("\r\n\r\n", 1)
                params = {}
                for par in body.split("&"):
                    if "=" in par:
                        k, v = par.split("=", 1)
                        params[k] = v

                fecha = params.get("fecha", "")
                hora = params.get("hora", "")

                datetime_str = f"{fecha} {hora}"
                reloj.set_datetime(estado.rtc, datetime_str)

                respuesta_redirect(writer, f"Hora actualizada a {datetime_str}")


            elif ruta == "/datalog.html":
                respuesta(writer, cargar_html("datalog.html"))

            elif ruta == "/download":
                try:
                    with open(config.CSV_PATH, "r") as f:
                        writer.write("HTTP/1.0 200 OK\r\nContent-Type: text/csv\r\n\r\n")
                        await writer.drain()
                        for linea in f:
                            writer.write(linea)
                            await writer.drain()
                except:
                    respuesta_redirect(writer, "No se pudo abrir el archivo")

            elif ruta == "/clear":
                storage.borrar_datos()
                errores.clear_error_Memoria()
                respuesta_redirect(writer, "Historial borrado")

  
            elif ruta == "/reset_error1":
                errores.clear_error_SinRemedio()
                respuesta_redirect(writer, "Error de dosificacion reseteado")

            elif ruta == "/config.html":
                html = cargar_html("config.html")
                cfg = storage.cargar_configuracion()
                html = html.replace("{{K_AGUA}}", str(cfg["k_agua"]))
                html = html.replace("{{K_REMEDIO}}", str(cfg["k_remedio"]))
                html = html.replace("{{DOSIS}}", str(cfg["dosis"]))
                respuesta(writer, html)

            # Otros endpoints podrían agregarse aquí...


            elif ruta.startswith("/guardar_k"):
                headers, body = data.decode().split("\r\n\r\n", 1)
                params = {}
                for par in body.split("&"):
                    if "=" in par:
                        k, v = par.split("=", 1)
                        params[k] = v

                try:
                    nuevo_k_agua = float(params.get("k_agua", "0"))
                    nuevo_k_remedio = float(params.get("k_remedio", "0"))

                    cfg = storage.cargar_configuracion()
                    cfg["k_agua"] = nuevo_k_agua
                    cfg["k_remedio"] = nuevo_k_remedio
                    storage.guardar_configuracion(cfg)

                    estado.agua.calibrar(nuevo_k_agua)
                    estado.remedio.calibrar(nuevo_k_remedio)

                    respuesta_redirect(writer, "Constantes de caudalímetros actualizadas correctamente")
                except Exception as e:
                    respuesta_redirect(writer, f"Error al guardar k: {e}", status=500)


            elif ruta.startswith("/guardar_dosis"):
                headers, body = data.decode().split("\r\n\r\n", 1)
                params = {}
                for par in body.split("&"):
                    if "=" in par:
                        k, v = par.split("=", 1)
                        params[k] = v

                try:
                    nueva_dosis = float(params.get("dosis", "0"))

                    cfg = storage.cargar_configuracion()
                    cfg["dosis"] = nueva_dosis
                    storage.guardar_configuracion(cfg)

                    estado.kar = nueva_dosis

                    respuesta_redirect(writer, "Dosis actualizada correctamente")
                except Exception as e:
                    respuesta_redirect(writer, f"Error al guardar dosis: {e}", status=500)

            else:
                respuesta_redirect(writer, "Ruta no encontrada", status=404)


        except Exception as e:
            respuesta_redirect(writer, f"Error interno: {e}", status=500)
        finally:
            await writer.drain()
            await writer.wait_closed()
            servidor_activo = True

    async def servidor():
        srv = await asyncio.start_server(handle, "0.0.0.0", config.HTTP_PORT)
        try:
            await asyncio.sleep(300)  # 5 minutos
        finally:
            srv.close()
            await srv.wait_closed()
            servidor_activo = False
            apagar_wifi()
            print("Apagar Servidor")

    await servidor()

# Enviar respuesta HTTP
def respuesta(writer, contenido, status=200):
    writer.write(f"HTTP/1.0 {status} OK\r\nContent-type: text/html\r\n\r\n")
    writer.write(contenido)

def respuesta_redirect(writer, mensaje, destino="/", segundos=5):
    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="{segundos}; url={destino}" />
    </head>
    <body>
        <p>{mensaje}</p>
        <p>Redirigiendo en {segundos} segundos...</p>
    </body>
    </html>
    """
    respuesta(writer, html)


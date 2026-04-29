

# server.py
from microdot_asyncio import Microdot, Response, send_file
import ujson

app = Microdot()
Response.default_content_type = 'text/html; charset=utf-8'

# referencias que setearás desde main_async.py
parametros = None
dosificar = None
bomba = None
estado_getter = None

# map identificadores -> (get,set,unit,label)
param_map = {
    'carga':      ('get_Carga','set_Carga','kg','Carga'),
    'dosis':      ('get_DosisDiariaFarmaco','set_DosisDiariaFarmaco','ml/100kg','Dosis'),
    'qbomba':     ('get_QBomba','set_QBomba','ml/s','Caudal Bomba'),
    'pulso':      ('get_tiempoEncendidoBomba','set_tiempoEncendidoBomba','s','Pulso'),
    'descanso':   ('get_tiempoDescansoBomba','set_tiempoDescansoBomba','s','Descanso'),
    'contraccion':('get_porcentajeContraccionTDAVB','set_porcentajeContraccionTDAVB','%','%Contraccion'),
    'qbebida':    ('get_QBebida','set_QBebida','l/min','Caudal Bebida'),
    'aguaconsumo':('get_aguaConsumidaPor100Kg','set_aguaConsumidaPor100Kg','l/100kg','Consumo agua'),
}

INDEX_PATH = '/html/index.html'

@app.route('/')
@app.route('/html/index.html')
async def index(req):
    return send_file(INDEX_PATH)

@app.route('/html/configuracion.html')
async def conf(req):
    return send_file('/html/configuracion.html')

@app.route('/html/config_item.html')
async def conf_item(req):
    return send_file('/html/config_item.html')

@app.route('/html/bombaManual.html')
async def bomba_manual(req):
    # poner sistema en latente
    if dosificar:
        try:
            dosificar.set_estado_latente()
        except Exception as e:
            print("error set_estado_latente:", e)
    return send_file('/html/bombaManual.html')

@app.route('/status')
async def status(req):
    if estado_getter:
        try:
            estado = estado_getter()
        except Exception as e:
            estado = {"error": str(e)}
    else:
        estado = {"info": "no estado_getter definido"}
    return Response(ujson.dumps(estado),
                    headers={'Content-Type': 'application/json'})

@app.route('/api/get_param')
async def api_get(req):
    q = req.args or {}
    name = q.get('name')
    if not name:
        return Response(ujson.dumps({"error": "missing name"}),
                        headers={'Content-Type': 'application/json'}, status=400)
    try:
        info = param_map.get(name)
        unit = info[2] if info else None
        val = None
        if parametros and info:
            getter = getattr(parametros, info[0], None)
            if getter:
                val = getter()
        return Response(ujson.dumps({"name": name, "value": val, "unit": unit}),
                        headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response(ujson.dumps({"error": str(e)}),
                        headers={'Content-Type': 'application/json'}, status_code=500)


@app.route('/api/set_param')
async def api_set(req):
    q = req.args or {}
    name = q.get('name')
    raw_value = q.get('value')
    print("api_set name:", name, "raw_value:", raw_value)

    if not name:
        return Response(ujson.dumps({"out": False, "msj": "missing name"}),
                        headers={'Content-Type': 'application/json'}, status_code=400)

    # convertir a número
    if raw_value is None or raw_value == '':
        value = None
    else:
        s = raw_value
        try:
            value = int(s)
            print("int:", value)
        except:
            try:
                value = float(s)
                print("float:", value)
            except:
                print("valor no numérico")
                return Response(
                    ujson.dumps({"out": False, "msj": "Valor no numérico"}),
                    headers={'Content-Type': 'application/json'}
                )

    try:
        info = param_map.get(name)
        print("param_map info:", info)
        if not info:
            return Response(ujson.dumps({"out": False, "msj": "param desconocido"}),
                            headers={'Content-Type': 'application/json'})
        setter = getattr(parametros, info[1], None) if parametros else None
        if not setter:
            return Response(ujson.dumps({"out": False, "msj": "setter no encontrado"}),
                            headers={'Content-Type': 'application/json'})
        result = setter(value)
        print("setter OK, result:", result)
        return Response(ujson.dumps(result), headers={'Content-Type': 'application/json'})
    except Exception as e:
        print("error en api_set:", e)
        return Response(ujson.dumps({"out": False, "msj": str(e)}),
                        headers={'Content-Type': 'application/json'}, status_code=500)


@app.route('/download/config')
async def download_config(req):
    try:
        from utils import datalog as _dlog
        fname = _dlog.exportarLogConfiguracion()
        if not fname:
            return Response(ujson.dumps({"error": "no file"}),
                            headers={'Content-Type': 'application/json'}, status_code=500)
        with open('/' + fname, 'rb') as f:
            data = f.read()
        return Response(
            data,
            headers={
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename="{}"'.format(fname)
            }
        )
    except Exception as e:
        print("download_config error:", e)
        return Response("Not found: {}".format(e), status_code=404)


@app.route('/download/operativo')
async def download_operativo(req):
    try:
        from utils import datalog as _dlog
        fname = _dlog.exportarLogOperativo()
        if not fname:
            return Response(ujson.dumps({"error": "no file"}),
                            headers={'Content-Type': 'application/json'}, status_code=500)
        with open('/' + fname, 'rb') as f:
            data = f.read()
        return Response(
            data,
            headers={
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename="{}"'.format(fname)
            }
        )
    except Exception as e:
        print("download_operativo error:", e)
        return Response("Not found: {}".format(e), status_code=404)


@app.route('/api/delete_history')
async def api_delete_history(req):
    try:
        from utils import datalog as _dlog
        res = _dlog.borrarHistoria()
        if isinstance(res, dict):
            payload = res
        else:
            payload = {"out": True, "msj": "Historia borrada"} if (res is None or res is True) \
                      else {"out": False, "msj": "No se pudo borrar"}
        return Response(ujson.dumps(payload),
                        headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response(ujson.dumps({"out": False, "msj": str(e)}),
                        headers={'Content-Type': 'application/json'}, status_code=500)


@app.route('/api/bomba/exit_manual')
async def api_bomba_exit(req):
    try:
        print("API exit_manual called")
        try:
            if bomba:
                bomba.apagar()
        except Exception as e:
            print("error apagando bomba:", e)
        try:
            if dosificar:
                dosificar.set_estado_operativo()
        except Exception as e:
            print("error set_estado_operativo:", e)
            return Response(ujson.dumps({"out": False, "msj": "error dosificar: " + str(e)}),
                            headers={'Content-Type': 'application/json'}, status_code=500)
        return Response(ujson.dumps({"out": True, "msj": "ok"}),
                        headers={'Content-Type': 'application/json'})
    except Exception as e:
        print("api_bomba_exit fatal:", e)
        return Response(ujson.dumps({"out": False, "msj": str(e)}),
                        headers={'Content-Type': 'application/json'}, status=500)


@app.route('/api/bomba/encender')
async def api_bomba_encender(req):
    try:
        if bomba:
            bomba.encender()
            return Response(ujson.dumps({"out": True}),
                            headers={'Content-Type': 'application/json'})
        else:
            return Response(ujson.dumps({"out": False, "msj": "no bomba"}),
                            headers={'Content-Type': 'application/json'}, status_code=500)
    except Exception as e:
        return Response(ujson.dumps({"out": False, "msj": str(e)}),
                        headers={'Content-Type': 'application/json'}, status_code=500)


@app.route('/api/bomba/apagar')
async def api_bomba_apagar(req):
    try:
        if bomba:
            bomba.apagar()
            return Response(ujson.dumps({"out": True}),
                            headers={'Content-Type': 'application/json'})
        else:
            return Response(ujson.dumps({"out": False, "msj": "no bomba"}),
                            headers={'Content-Type': 'application/json'}, status_code=500)
    except Exception as e:
        return Response(ujson.dumps({"out": False, "msj": str(e)}),
                        headers={'Content-Type': 'application/json'}, status_code=500)


@app.route('/api/bomba/status')
async def api_bomba_status(req):
    try:
        enc = False
        if bomba and hasattr(bomba, 'esta_encendida'):
            enc = bool(bomba.esta_encendida())
        return Response(ujson.dumps({"encendida": enc}),
                        headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response(ujson.dumps({"error": str(e)}),
                        headers={'Content-Type': 'application/json'}, status_code=500)

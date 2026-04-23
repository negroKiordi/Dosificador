# main_async.py
import esp, gc
esp.osdebug(None)
gc.collect()

import uasyncio as asyncio
import utime
import config

# importa tus módulos de instrumentación como antes
from utils.cvalvula_bebedero import CvalvulaBebedero
from utils.cparametros_operativos import CParametrosOperativos
from utils.cbomba_farmaco import CBombaFarmaco
from utils.ctdavb import CTDAVB
from utils.cdosificar import CDosificar
from utils.ctiempo import CTiempo
from utils.cdatalog import CDatalog

# importa el wifi manager asíncrono
from utils.cwifimanager_async import CWifiManager

def crear_get_estado(tiempo, parametros, valvula, bomba, ctdavb, dosificar):
    def getter():
        try:
            # tiempo
            fecha = tiempo.fecha()
            hora  = tiempo.hora()

            # ctdavb
            tdavb = None
            tavb = None
            tavb_pct = None
            try:
                tdavb = ctdavb.tiempoDiarioApertura()
            except:
                tdavb = None
                print("Error al obtener datos de ctdavb")
            try:
                tavb = ctdavb.tiempoAperturaAcumulado()   # en minutos si tu método lo da así
            except:
                tavb = None
                print("Error al obtener datos de ctdavb")
            try:
                tavb_pct = ctdavb.tiempoAperturaAcumuladoPorcentaje()
            except:
                tavb_pct = None
                print("Error al obtener datos de ctdavb")

            # dosificar
            remedio = None
            remedio_pct = None
            try:
                remedio = dosificar.remedioAcumulado()
            except:
                remedio = None
                print("Error al obtener datos de dosificar 1")
            try:
                remedio_pct = dosificar.remedioAcumuladoPorcentaje()
            except:
                remedio_pct = None
                print("Error al obtener datos de dosificar 2")

            # parametros: usar get_all() (rápido)
            try:
                params = parametros.get_all()
                # opcional: añadir derived params
                carga = params.get('carga')
                dosis_per_100 = params.get('dosis_diaria_farmaco')
                dosis_diaria = None
                if carga is not None and dosis_per_100 is not None:
                    dosis_diaria = (carga * dosis_per_100) / 100.0
                params['DosisDiaria'] = dosis_diaria
            except:
                params = {}
                print("Error al obtener parámetros operativos:", params)

            # capacidad (valores de ejemplo; define cargaMax en config o parámetros)
            carga_max = getattr(config, 'CARGA_MAXIMA', None)
            dosis_diaria_max = None
            if carga_max is not None and params.get('dosis_diaria_farmaco') is not None:
                dosis_diaria_max = (carga_max * params.get('ddosis_diaria_farmaco')) / 100.0
 
            estado = {
                "fecha": fecha,
                "hora": hora,
                "ctdavb": {
                    "tiempoDiarioApertura": tdavb,
                    "tiempoAperturaAcumulado": tavb,
                    "tiempoAperturaAcumuladoPorcentaje": tavb_pct
                },
                "dosificar": {
                    "remedioAcumulado": remedio,
                    "remedioAcumuladoPorcentaje": remedio_pct
                },
                "parametros": params,
                "capacidad": {
                    "cargaMaxima": carga_max,
                    "dosisDiariaMaxima": dosis_diaria_max
                }
            }
            print(estado)
        except Exception as e:
            print("Error al obtener estado completo:", e)
            estado = {"error": str(e)}

        return estado
    return getter

async def tarea_operativa(tiempo):
    intervalo_ms = 1000
    ultimo = utime.ticks_ms()
    while True:
        ahora = utime.ticks_ms()
        if utime.ticks_diff(ahora, ultimo) >= intervalo_ms:
            tiempo.procesar_tick()
            ultimo = ahora
        await asyncio.sleep_ms(10)

def main():
    print("\nIniciando sistema (async)...")
    gc.collect()

    parametros = CParametrosOperativos()
    valvula = CvalvulaBebedero(pin=config.VALVULA_PIN)
    bomba   = CBombaFarmaco(pin=config.BOMBA_PIN, parametros=parametros)
    tiempo  = CTiempo(sda_pin=config.TIEMPO_SDA_PIN, scl_pin=config.TIEMPO_SCL_PIN, parametros=parametros)
    ctdavb  = CTDAVB(parametros)
    dosificar = CDosificar(bomba, parametros, ctdavb)
    datalog = CDatalog(tiempo, parametros, valvula, bomba, ctdavb, dosificar)

    # Vinculaciones igual que antes
    valvula.listaCambioValvula(ctdavb)
    valvula.listaCambioValvula(dosificar)
    ctdavb.valvulaBebedero(valvula)
    tiempo.listaNuevoDia(ctdavb)
    tiempo.listaNuevoDia(dosificar)
    tiempo.listaNuevoDia(datalog)
    tiempo.listaTick(valvula)
    tiempo.listaTick(ctdavb)
    tiempo.listaTick(bomba)
    tiempo.listaTick(dosificar)
    tiempo.listaTick(bomba)
    
    # Data Logger (singleton global)
    from utils.datalog import init as datalog_init
    datalog_init(tiempo, parametros, valvula, bomba, ctdavb, dosificar)


    estado_getter = crear_get_estado(tiempo, parametros, valvula, bomba, ctdavb, dosificar)
    wifi_manager = CWifiManager(estado_getter=estado_getter)

    loop = asyncio.get_event_loop()
    loop.create_task(tarea_operativa(tiempo))
    loop.create_task(wifi_manager.run())
    loop.run_forever()

if __name__ == "__main__":
    main()

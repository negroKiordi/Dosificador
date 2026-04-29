# main.py
import uasyncio as asyncio
import utime
import config

from utils.cvalvula_bebedero import CvalvulaBebedero
from utils.cparametros_operativos import CParametrosOperativos
from utils.cbomba_farmaco import CBombaFarmaco
from utils.ctdavb import CTDAVB
from utils.cdosificar import CDosificar
from utils.ctiempo import CTiempo
from utils.cdatalog import CDatalog
from utils.datalog import avisoEvento, init as datalog_init
from utils.ceventos import Eventos

from tarea_wifi import tarea_wifi
from server import app  # Microdot
import server           # para setear referencias


def crear_get_estado(tiempo, parametros, valvula, bomba, ctdavb, dosificar):
    def getter():
        try:
            # tiempo
            fecha = tiempo.fecha()
            hora  = tiempo.hora()
            # ctdavb
            tdavb = ctdavb.tiempoDiarioApertura()  
            tdavbacc = ctdavb.tiempoAperturaAcumulado()   # En segundos
            tavb_pct = ctdavb.tiempoAperturaAcumuladoPorcentaje()
            # dosificar
            remedio = dosificar.remedioAcumulado()
            remedio_pct = dosificar.remedioAcumuladoPorcentaje()
            estado = {
                "fecha": fecha, 
                "hora": hora,
                "ctdavb": {
                    "tiempoDiarioApertura": tdavb,
                    "tiempoAperturaAcumulado": tdavbacc,
                    "tiempoAperturaAcumuladoPorcentaje": tavb_pct
                },
                "dosificar": {
                    "remedioAcumulado": remedio,
                    "remedioAcumuladoPorcentaje": remedio_pct
                },
            }
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

async def main_async():
    print("\nIniciando sistema (async + Microdot estándar)...")

    parametros = CParametrosOperativos()
    valvula = CvalvulaBebedero(pin=config.VALVULA_PIN)
    bomba   = CBombaFarmaco(pin=config.BOMBA_PIN, parametros=parametros)
    tiempo  = CTiempo(sda_pin=config.TIEMPO_SDA_PIN, scl_pin=config.TIEMPO_SCL_PIN, parametros=parametros)
    ctdavb  = CTDAVB(parametros)
    dosificar = CDosificar(bomba, parametros, ctdavb)
    datalog = CDatalog(tiempo, parametros, valvula, bomba, ctdavb, dosificar)

    # vínculos como antes
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

    datalog_init(tiempo, parametros, valvula, bomba, ctdavb, dosificar)

    if not tiempo.reencendio():
        avisoEvento(Eventos.ENCENDIDO)
    else:
        avisoEvento(Eventos.REENCENDIDO)

    estado_getter = crear_get_estado(tiempo, parametros, valvula, bomba, ctdavb, dosificar)

    # pasar referencias al módulo server
    server.estado_getter = estado_getter
    server.parametros = parametros
    server.dosificar = dosificar
    server.bomba = bomba

    # lanzar tareas
    asyncio.create_task(tarea_operativa(tiempo))
    asyncio.create_task(tarea_wifi())

    # arrancar servidor HTTP (Microdot) en este mismo loop
    await app.start_server(host='0.0.0.0', port=80)

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()

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

def crear_get_estado(tiempo, parametros, valvula, bomba, dosificar):
    def getter():
        try:
            estado = {
                "fecha": tiempo.fecha(),
                "hora": tiempo.hora(),
                "valvula": "abierta" if valvula.valvulaAbierta() else "cerrada",
                "bomba": "on" if bomba.esta_encendida() else "off",
                "param": {
                    "Carga": parametros.get_Carga(),
                    "DosisDiaria": parametros.get_DosisDiariaFarmaco()
                }
            }
        except Exception as e:
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
    tiempo.listaTick(dosificar)
    tiempo.listaTick(bomba)
    
    # Data Logger (singleton global)
    from utils.datalog import init as datalog_init
    datalog_init(tiempo, parametros, valvula, bomba, ctdavb, dosificar)


    estado_getter = crear_get_estado(tiempo, parametros, valvula, bomba, dosificar)
    wifi_manager = CWifiManager(estado_getter=estado_getter)

    loop = asyncio.get_event_loop()
    loop.create_task(tarea_operativa(tiempo))
    loop.create_task(wifi_manager.run())
    loop.run_forever()

if __name__ == "__main__":
    main()

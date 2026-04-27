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
from utils.datalog import avisoEvento
from utils.ceventos import Eventos


# importa el wifi manager asíncrono
from utils.cwifimanager_async import CWifiManager

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

            # parametros: usar get_all() (rápido)
            params = parametros.get_all()
            carga = params.get('carga')
            dosis_per_100 = params.get('dosis_diaria_farmaco')
            dosis_diaria = None
            if carga is not None and dosis_per_100 is not None:
                dosis_diaria = (carga * dosis_per_100) / 100.0
            params['DosisDiaria'] = dosis_diaria
 
            # capacidad (valores de ejemplo; define cargaMax en config o parámetros)
            carga_max = params.get('carga_maxima_abrevable')  
            q_bomba_minimo = params.get('q_bomba_minimo')
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
                "parametros": params,
                "capacidad": {
                    "cargaMaxima": carga_max,
                    "qbombaminimo": q_bomba_minimo
                }
            }
            #print(estado)
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

    if not tiempo.reencendio():
        print("\n✅ [main] El sistema se reencendió después de haber estado apagado. Se han reiniciado los acumulados diarios.")
        avisoEvento(Eventos.ENCENDIDO)
    else:
        print("\n✅ [main] El sistema se reencendió rápidamente. No se reiniciaron los acumulados diarios.")
        avisoEvento(Eventos.REENCENDIDO)

    estado_getter = crear_get_estado(tiempo, parametros, valvula, bomba, ctdavb, dosificar)
    wifi_manager = CWifiManager(estado_getter=estado_getter,parametros=parametros,dosificar=dosificar,bomba=bomba) 

    loop = asyncio.get_event_loop()
    loop.create_task(tarea_operativa(tiempo))
    loop.create_task(wifi_manager.run())
    loop.run_forever()

if __name__ == "__main__":
    main()

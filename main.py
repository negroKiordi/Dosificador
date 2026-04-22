# main.py
# =============================================================================
# DOSIFICADOR DE CARMINATIVO ANTI-EMPASTE - Versión con temporización precisa
# =============================================================================


import esp
esp.osdebug(None)        # Desactiva mensajes de debug del ESP (ahorra RAM)
import gc
gc.collect()
print("Memoria inicial libre:", gc.mem_free(), "bytes")

import machine
import utime
import gc 
import config

# Importamos desde la subcarpeta utils/
from utils.interfaces import IValvulaListener, INuevoDia, ITick
from utils.cvalvula_bebedero import CvalvulaBebedero
from utils.cparametros_operativos import CParametrosOperativos
from utils.cbomba_farmaco import CBombaFarmaco
from utils.ctdavb import CTDAVB
from utils.cdosificar import CDosificar
from utils.ctiempo import CTiempo
from utils.cdatalog import CDatalog


def main():
    print("\n" + "="*70)
    print("🚀 INICIANDO DOSIFICADOR DE CARMINATIVO ANTI-EMPASTE")
    print("="*70)

    # 1. Parámetros operativos
    parametros = CParametrosOperativos()

    print("   Carga actual       :", parametros.get_Carga(), "kg")
    print("   Dosis diaria       :", parametros.get_DosisDiariaFarmaco(), "ml/100 kg")
    print("   QBomba             :", parametros.get_QBomba(), "ml/seg")
    print("   Tiempo encendido   :", parametros.get_tiempoEncendidoBomba(), "seg") 
    print("   Tiempo de descaso  :", parametros.get_tiempoDescansoBomba(), "seg")
    print("   % contracción TDAVB:", parametros.get_porcentajeContraccionTDAVB(), "%")

    # 2. Hardware
    valvula = CvalvulaBebedero(pin=config.VALVULA_PIN)
    bomba   = CBombaFarmaco(pin=config.BOMBA_PIN, parametros=parametros)
    
    # 3. Núcleo del sistema
    tiempo  = CTiempo(sda_pin=config.TIEMPO_SDA_PIN, scl_pin=config.TIEMPO_SCL_PIN, parametros=parametros) 
    ctdavb  = CTDAVB(parametros)
    dosificar = CDosificar(bomba, parametros, ctdavb)
    datalog = CDatalog(tiempo, parametros, valvula, bomba, ctdavb, dosificar)
    
    # 4. Vinculación de callbacks
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



    # 5. Data Logger (singleton global)
    from utils.datalog import init as datalog_init
    datalog_init(tiempo, parametros, valvula, bomba, ctdavb, dosificar)

    print("\n✅ SISTEMA INICIADO CORRECTAMENTE")
    print(" Válvula → GPIO", config.VALVULA_PIN)
    print(" Bomba   → GPIO", config.BOMBA_PIN)
    print(" RTC     → SDA=", config.TIEMPO_SDA_PIN, " SCL=", config.TIEMPO_SCL_PIN)
    print(" Botón WiFi → GPIO", config.PIN_BOTON_WIFI)


    # =============================================================================
    # Bucle principal con temporización precisa
    # =============================================================================

    gc.collect()
    try:
        from utils.cwifimanager import CWifiManager
        wifi_manager = CWifiManager()
        gc.collect()
        print("✅ WiFi Manager cargado | Memoria libre:", gc.mem_free())
    except MemoryError as e:
        print("❌ MemoryError al cargar WiFi:", e)
        print("Memoria disponible:", gc.mem_free())
        utime.sleep(3)
        # machine.reset()   # descomenta si quieres reiniciar automáticamente


    print("Botón WiFi listo en GPIO", config.PIN_BOTON_WIFI)

    intervalo_ms = 1000
    ultimo_tick = utime.ticks_ms()

    while True:
        ahora = utime.ticks_ms()
       
        if utime.ticks_diff(ahora, ultimo_tick) >= intervalo_ms:
            tiempo.procesar_tick()
            ultimo_tick = ahora

        wifi_manager.process()

        utime.sleep_ms(10)




if __name__ == "__main__":
    main()

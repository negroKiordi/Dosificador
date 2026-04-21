# main.py
# =============================================================================
# DOSIFICADOR DE CARMINATIVO ANTI-EMPASTE - Versión con temporización precisa
# =============================================================================

import machine
import utime

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

    # 1. Parametros operativos
    parametros = CParametrosOperativos()

    print("   Carga actual       :", parametros.get_Carga(), "kg")
    print("   Dosis diaria       :", parametros.get_DosisDiariaFarmaco(), "ml/100 kg")
    print("   QBomba             :", parametros.get_QBomba(), "ml/seg")
    print("   Tiempo encendido   :", parametros.get_tiempoEncendidoBomba(), "seg") 
    print("   Tiempo de descaso  :", parametros.get_tiempoDescansoBomba(), "seg")
    print("   % contracción TDAVB:", parametros.get_porcentajeContraccionTDAVB(), "%")

    # 2. Instanciacion de los objetos de trabajo.
    ctdavb  = CTDAVB(parametros)
    dosificar = CDosificar(bomba, parametros, ctdavb)
    datalog = CDatalog(tiempo, parametros, valvula, bomba, ctdavb, dosificar)

    # 3. Instanciacion del Hardware
    bomba   = CBombaFarmaco(pin=config.BOMBA_PIN, parametros=parametros)
    valvula = CvalvulaBebedero(pin=config.VALVULA_PIN) 
    # Registro las Callback de Cambio Estado en el objeto valvula
    valvula.listaCambioValvula(ctdavb)
    valvula.listaCambioValvula(dosificar)
    
    # 4. Instancio la Clase CTiempo
    tiempo  = CTiempo(sda_pin=config.TIEMPO_SDA_PIN, 
                      scl_pin=config.TIEMPO_SCL_PIN, 
                      parametros=parametros) 
    
    # Registro las Callback de Nuevo Dia en el objeto tiempo
    tiempo.listaNuevoDia(ctdavb)
    tiempo.listaNuevoDia(dosificar)
    tiempo.listaNuevoDia(datalog)        

    # Registro las Callback de Tick en el objeto tiempo
    # Controlar el orden en que deberían registrarse.
    tiempo.listaTick(valvula)
    tiempo.listaTick(ctdavb)
    tiempo.listaTick(bomba)
    tiempo.listaTick(dosificar)

    # 5. Completo Configuración de los objetos instanciados.
    ctdavb.valvulaBebedero(valvula)

    # 6. Data Logger (singleton global)
    from utils.datalog import init as datalog_init
    datalog_init(tiempo, parametros, valvula, bomba, ctdavb, dosificar)
    # Ya se puede usar el objeto datalog = CDatalog (...)
    #    en cualquier parte del código:


    print("\n✅ SISTEMA INICIADO CORRECTAMENTE")
    print("   Válvula → GPIO", config.VALVULA_PIN)
    print("   Bomba   → GPIO", config.BOMBA_PIN)
    print("   RTC     → SDA=", config.TIEMPO_SDA_PIN, "  SCL=", config.TIEMPO_SCL_PIN)

    # =============================================================================
    # TEMPORIZACIÓN PRECISA (ejecuta procesar_tick() exactamente cada 1000 ms)
    # =============================================================================
    intervalo_ms = 1000                     # 1 segundo
    proximo_tick = utime.ticks_ms() # Proximo momento para procesar_tick()

    print("Iniciando bucle principal con temporización precisa...")

    while True:
        ahora = utime.ticks_ms() # Momento presente
        
        # Ejecutamos procesar_tick() solo cuando ha pasado 1 segundo
        if utime.ticks_diff(ahora, proximo_tick) >= 0:
            # Ha llegado el momento de invocar procesar_tick.
            # ahora es el instante de entrada a tiempo.procesar_tick()
            tiempo.procesar_tick()

            # Medimos el tiempo de procesamiento de cada Tick
            tiempoProcesamiento = utime.ticks_diff(utime.ticks_ms(), ahora)
            if tiempoProcesamiento >= intervalo_ms:
                # Si tiempo de procesamiento > 1000 ms
                print("Uops, Mucho tiempo de Procesamiento = ", 
                      tiempoProcesamiento, "ms")
            
            proximo_tick += intervalo_ms # Sumo intervalo_ms

        else: utime.sleep_ms(10) # Para no saturar CPU, muy importante en ESP8266


if __name__ == "__main__":
    main()
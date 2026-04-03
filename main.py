# main.py
# =============================================================================
# DOSIFICADOR DE CARMINATIVO ANTI-EMPASTE - Versión completa
# =============================================================================

import machine
import utime

import config                                   # configuración central

# Importamos desde la subcarpeta utils/
from utils.interfaces import IValvulaListener, INuevoDia, ITick
from utils.valvula_bebedero import ValvulaBebedero
from utils.cparametros_operativos import CParametrosOperativos
from utils.cbomba_farmaco import CBombaFarmaco
from utils.ctdavb import CTDAVB
from utils.cdosificar import CDosificar
from utils.ctiempo import CTiempo


def main() -> None:
    print("\n" + "="*70)
    print("🚀 INICIANDO DOSIFICADOR DE CARMINATIVO ANTI-EMPASTE")
    print("="*70)

    # 1. Parámetros operativos → se cargan automáticamente desde parametros.json
    #    (o se crean con defaults de config.py si no existe el archivo)
    parametros = CParametrosOperativos()

    # Mostramos los valores que realmente se están usando
    print(f"   Carga actual       : {parametros.get_Carga()} kg")
    print(f"   Dosis diaria       : {parametros.get_DosisDiariaFarmaco()} ml/100 kg")
    print(f"   QBomba             : {parametros.get_QBomba()} ml/seg")
    print(f"   % contracción TDAVB: {parametros.get_porcentajeContraccionTDAVB()}%")

    # 2. Hardware
    valvula = ValvulaBebedero(pin=config.VALVULA_PIN)
    bomba   = CBombaFarmaco(pin=config.BOMBA_PIN, parametros=parametros)
    
    # 3. Núcleo del sistema
    tiempo  = CTiempo(sda_pin=config.TIEMPO_SDA_PIN, scl_pin=config.TIEMPO_SCL_PIN)
    ctdavb  = CTDAVB(parametros)
    dosificar = CDosificar(bomba=bomba, parametros=parametros, ctdavb=ctdavb)

    # 4. Vinculación de callbacks
    valvula.listaCambioValvula(ctdavb)
    valvula.listaCambioValvula(dosificar)

    ctdavb.CvalvulaBebedero(valvula)

    tiempo.listaNuevoDia(ctdavb)
    tiempo.listaNuevoDia(dosificar)

    tiempo.listaTick(valvula)
    tiempo.listaTick(ctdavb)
    tiempo.listaTick(dosificar)

    print("\n✅ SISTEMA INICIADO CORRECTAMENTE")
    print(f"   Válvula → GPIO {config.VALVULA_PIN}")
    print(f"   Bomba   → GPIO {config.BOMBA_PIN}")
    print(f"   RTC     → SDA={config.TIEMPO_SDA_PIN}  SCL={config.TIEMPO_SCL_PIN}")

    # Bucle principal
    while True:
        tiempo.procesar_tick()
        utime.sleep(1)


if __name__ == "__main__":
    main()

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
# Ya se puede usar en cualquier parte del código:
# from utils.datalog import datalog
# datalog.avisoEvento(Eventos.NUEVO_DIA)


print("\n✅ SISTEMA INICIADO CORRECTAMENTE")
print("   Válvula → GPIO", config.VALVULA_PIN)
print("   Bomba   → GPIO", config.BOMBA_PIN)
print("   RTC     → SDA=", config.TIEMPO_SDA_PIN, "  SCL=", config.TIEMPO_SCL_PIN)

x = datalog.exportarLogOperativo()  # Exportamos el log al iniciar el sistema


print(x)
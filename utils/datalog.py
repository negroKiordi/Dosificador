# utils/datalog.py 
"""
Singleton global del Data Logger.
Importar y usar desde cualquier parte del proyecto.
La Clase CDatalog levanta una excepción si se pretende 
    crear más que una instancia.
Doble control
"""

_datalog = None

def init(tiempo, parametros, valvula, bomba, ctdavb, dosificar):
    """LLAMAR UNA SOLA VEZ desde main.py"""
    global _datalog
    if _datalog is not None:
        print("⚠️  CDatalog ya estaba inicializado")
        return False

    from utils.cdatalog import CDatalog

    _datalog = CDatalog(tiempo, parametros, valvula, bomba, ctdavb, dosificar)
    tiempo.listaNuevoDia(_datalog)  # Asegura que CDatalog reciba el evento de nuevo día

    print("✅ objeto CDatalog global inicializado correctamente")
    return True

def avisoEventoConfig(event_code):
    """Función global para registrar eventos desde cualquier parte"""
    global _datalog
    if _datalog is None:
        print("⚠️  CDatalog no inicializado aún")
        return
    _datalog.avisoEventoConfiguracion(event_code)


def avisoEvento(event_code):
    """Función global para registrar eventos desde cualquier parte"""
    global _datalog
    if _datalog is None:
        print("⚠️  CDatalog no inicializado aún")
        return
    _datalog.avisoEventoOperativo(event_code)

def borrarHistoria():
    global _datalog
    if _datalog is None:
        print("⚠️  CDatalog no inicializado aún")
        return
    _datalog.borrarHistoria()

def exportarLogConfiguracion():
    global _datalog
    return _datalog.exportarLogConfiguracion() if _datalog else None


def exportarLogOperativo():
    global _datalog
    return _datalog.exportarLogOperativo() if _datalog else None
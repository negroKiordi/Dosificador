# utils/cparametros_operativos.py
import ujson
import config

class CParametrosOperativos:
    """
    Gestiona los parámetros operativos.
    - Carga desde parametros.json
    - Si no existe el archivo → crea uno nuevo con los DEFAULT_PARAMETROS de config.py
    """

    def __init__(self):
        self._valores = config.DEFAULT_PARAMETROS.copy()
        self._load()
        print("CParametrosOperativos cargados desde config.py + parametros.json")

    def _load(self):
        """Carga desde el archivo JSON. Si no existe, lo crea con defaults."""
        try:
            with open(config.ARCHIVO_PARAMETROS, "r") as f:
                datos = ujson.load(f)
                self._valores.update(datos)
            print("Parámetros cargados desde", config.ARCHIVO_PARAMETROS)
        except (OSError, ValueError):
            print("Archivo", config.ARCHIVO_PARAMETROS, "no encontrado o corrupto.")
            print("Creando nuevo archivo con valores por defecto de config.py")
            self._save()

    def _save(self):
        """Guarda los valores actuales en el archivo JSON."""
        try:
            with open(config.ARCHIVO_PARAMETROS, "w") as f:
                ujson.dump(self._valores, f)
        except OSError:
            print("No se pudo guardar parametros.json")

    # ================================================================
    # GET / SET
    # ================================================================
    def get_Carga(self):
        return self._valores["carga"]

    def set_Carga(self, carga):
        if carga < 0:
            carga = 0
        self._valores["carga"] = carga
        self._save()
        return carga

    def get_DosisDiariaFarmaco(self):
        return self._valores["dosis_diaria_farmaco"]

    def set_DosisDiariaFarmaco(self, dosis):
        if dosis < 0:
            dosis = 0.0
        self._valores["dosis_diaria_farmaco"] = dosis
        self._save()
        return dosis

    def get_QBomba(self):
        return self._valores["q_bomba"]

    def set_QBomba(self, caudal):
        if caudal <= 0:
            caudal = config.DEFAULT_PARAMETROS["q_bomba"]
        self._valores["q_bomba"] = caudal
        self._save()
        return caudal

    def get_porcentajeContraccionTDAVB(self):
        return self._valores["porcentaje_contraccion_tdavb"]

    def set_porcentajeContraccionTDAVB(self, valor):
        if valor < 1:
            valor = 1
        elif valor > 99:
            valor = 99
        self._valores["porcentaje_contraccion_tdavb"] = valor
        self._save()
        return valor

    def get_tiempoEncendidoBomba(self):
        """Retorna el tiempo que la bomba debe estar encendida (segundos)."""
        return self._valores["tiempo_encendido_bomba"]

    def set_tiempoEncendidoBomba(self, valor):
        """Fija el tiempo de encendido (mínimo 1 segundo)."""
        if valor < 1:
            valor = 1
        self._valores["tiempo_encendido_bomba"] = valor
        self._save()
        return valor

    def get_tiempoDescansoBomba(self):
        """Retorna el tiempo mínimo de descanso entre dosificaciones (segundos)."""
        return self._valores["tiempo_descanso_bomba"]
    
    def set_tiempoDescansoBomba(self, valor):
        """Fija el tiempo mínimo de descanso (mínimo 0 segundos)."""
        if valor < 0:
            valor = 0
        self._valores["tiempo_descanso_bomba"] = valor
        self._save()
        return valor    

    def get_QBebida(self):
        return self._valores["q_bebida"]

    def set_QBebida(self, caudal):
        if caudal <= 0:
            caudal = config.DEFAULT_PARAMETROS["q_bebida"]
        self._valores["q_bebida"] = caudal
        self._save()
        return caudal
 
    def get_aguaConsumidaPor100Kg(self):
        return self._valores["agua_consumida_por100Kg"]
 
    def set_aguaConsumidaPor100Kg(self, valor):
        if valor < 0:
            valor = 0
        self._valores["agua_consumida_por100Kg"] = valor
        self._save()
        return valor    

    def get_all(self):
        """Devuelve copia de todos los parámetros (útil para web)."""
        return self._valores.copy()
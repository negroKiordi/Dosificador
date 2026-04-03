# utils/cparametros_operativos.py
import ujson
import config
from typing import Dict

class CParametrosOperativos:
    """
    Gestiona los parámetros operativos.
    - Carga desde parametros.json
    - Si no existe el archivo → crea uno nuevo con los DEFAULT_PARAMETROS de config.py
    """

    def __init__(self) -> None:
        self._valores: Dict = config.DEFAULT_PARAMETROS.copy()
        self._load()
        print("✅ CParametrosOperativos cargados desde config.py + parametros.json")

    def _load(self) -> None:
        """Carga desde el archivo JSON. Si no existe, lo crea con defaults."""
        try:
            with open(config.ARCHIVO_PARAMETROS, "r") as f:
                datos = ujson.load(f)
                self._valores.update(datos)
            print(f"Parámetros cargados desde {config.ARCHIVO_PARAMETROS}")
        except (OSError, ValueError):
            print(f"Archivo {config.ARCHIVO_PARAMETROS} no encontrado o corrupto.")
            print("Creando nuevo archivo con valores por defecto de config.py")
            self._save()

    def _save(self) -> None:
        """Guarda los valores actuales en el archivo JSON."""
        try:
            with open(config.ARCHIVO_PARAMETROS, "w") as f:
                ujson.dump(self._valores, f)
        except OSError:
            print("⚠️  No se pudo guardar parametros.json")

    # ================================================================
    # GET / SET (igual que antes)
    # ================================================================
    def get_Carga(self) -> int:
        return self._valores["carga"]

    def set_Carga(self, carga: int) -> int:
        if carga < 0:
            carga = 0
        self._valores["carga"] = carga
        self._save()
        return carga

    def get_DosisDiariaFarmaco(self) -> float:
        return self._valores["dosis_diaria_farmaco"]

    def set_DosisDiariaFarmaco(self, dosis: float) -> float:
        if dosis < 0:
            dosis = 0.0
        self._valores["dosis_diaria_farmaco"] = dosis
        self._save()
        return dosis

    def get_QBomba(self) -> float:
        return self._valores["q_bomba"]

    def set_QBomba(self, caudal: float) -> float:
        if caudal <= 0:
            caudal = config.DEFAULT_PARAMETROS["q_bomba"]
        self._valores["q_bomba"] = caudal
        self._save()
        return caudal

    def get_cadenciaTick(self) -> int:
        return self._valores["cadencia_tick"]

    def set_cadenciaTick(self, cadencia: int) -> int:
        if cadencia < 1:
            cadencia = 1
        self._valores["cadencia_tick"] = cadencia
        self._save()
        return cadencia

    def get_porcentajeContraccionTDAVB(self) -> int:
        return self._valores["porcentaje_contraccion_tdavb"]

    def set_porcentajeContraccionTDAVB(self, valor: int) -> int:
        if valor < 1:
            valor = 1
        elif valor > 99:
            valor = 99
        self._valores["porcentaje_contraccion_tdavb"] = valor
        self._save()
        return valor

    def get_tiempoMinEncendidoBomba(self) -> int:
        """Retorna el tiempo mínimo que la bomba debe estar encendida (segundos)."""
        return self._valores["tiempo_min_encendido_bomba"]

    def set_tiempoMinEncendidoBomba(self, valor: int) -> int:
        """Fija el tiempo mínimo de encendido (mínimo 1 segundo)."""
        if valor < 1:
            valor = 1
        self._valores["tiempo_min_encendido_bomba"] = valor
        self._save()
        return valor

    def get_all(self) -> Dict:
        """Devuelve copia de todos los parámetros (útil para web)."""
        return self._valores.copy()
# ctdavb.py
import ujson
from typing import Optional
from interfaces import IValvulaListener, INuevoDia, ITick
from cparametros_operativos import CParametrosOperativos
from valvula_bebedero import ValvulaBebedero

# Archivo para persistir el TDAVB del día anterior
ARCHIVO_TDAVB = "tdavb_anterior.json"

class CTDAVB(IValvulaListener, INuevoDia, ITick):
    """
    Clase Tiempo Diario de Apertura de la Válvula del Bebedero (CTDAVB).
    """

    def __init__(self, parametros: CParametrosOperativos) -> None:
        self._parametros = parametros
        self._valvula: Optional[ValvulaBebedero] = None

        # Variables de estado
        self._tiempo_acumulado_hoy: int = 0          # segundos reales de apertura hoy
        self._tdavb_anterior: int = 0                # TDAVB del día anterior (segundos)
        self._esta_abierta: bool = False

        self._load_tdavb_anterior()

        print("✅ CTDAVB iniciada - TDAVB anterior:", self._tdavb_anterior, "segundos")

    # ================================================================
    # MÉTODOS DE CONFIGURACIÓN
    # ================================================================
    def CvalvulaBebedero(self, valvula: ValvulaBebedero) -> None:
        """Registra la válvula y sincroniza el estado inicial."""
        self._valvula = valvula
        # Sincronizamos el flag con la realidad física en el momento de la conexión
        if self._valvula is not None:
            self._esta_abierta = self._valvula.valvulaAbierta()

    def CParametrosOperativos(self, parametros: CParametrosOperativos) -> None:
        self._parametros = parametros

    # ================================================================
    # INTERFACES IMPLEMENTADAS
    # ================================================================
    def avisoCambioEstadoVB(self, estado: bool) -> None:
        """Notificación de cambio de estado de la válvula."""
        self._esta_abierta = estado

    def avisoNuevoDia(self) -> None:
        """00:00 → guardamos TDAVB de ayer y reseteamos contador del nuevo día.
           ¡NO tocamos el estado actual de la válvula!"""
        self._tdavb_anterior = self._tiempo_acumulado_hoy
        self._save_tdavb_anterior()

        self._tiempo_acumulado_hoy = 0
        # ←←← SE ELIMINÓ la línea self._esta_abierta = False

        # Opcional: re-sincronizamos por si hubo algún glitch de reloj
        if self._valvula is not None:
            self._esta_abierta = self._valvula.valvulaAbierta()

        print(f"[CTDAVB] Nuevo día → TDAVB anterior guardado: {self._tdavb_anterior} segundos")

    def tick(self, cadencia: int) -> None:
        """Acumula tiempo solo si la válvula está realmente abierta."""
        if self._esta_abierta:
            self._tiempo_acumulado_hoy += cadencia

    # ================================================================
    # MÉTODOS DE CONSULTA (documento original)
    # ================================================================
    def tiempoDiarioApertura(self) -> int:
        """TDAVB a usar para dosificación (día anterior × porcentaje)."""
        porcentaje = self._parametros.get_porcentajeContraccionTDAVB()
        return int(self._tdavb_anterior * porcentaje / 100)

    def tiempoAperturaAcumulado(self) -> int:
        """Tiempo real acumulado desde las 00:00 de hoy."""
        return self._tiempo_acumulado_hoy

    # ================================================================
    # PERSISTENCIA
    # ================================================================
    def _load_tdavb_anterior(self) -> None:
        try:
            with open(ARCHIVO_TDAVB, "r") as f:
                datos = ujson.load(f)
                self._tdavb_anterior = datos.get("tdavb_anterior", 0)
        except (OSError, ValueError):
            self._tdavb_anterior = 0

    def _save_tdavb_anterior(self) -> None:
        try:
            with open(ARCHIVO_TDAVB, "w") as f:
                ujson.dump({"tdavb_anterior": self._tdavb_anterior}, f)
        except OSError:
            print("⚠️  No se pudo guardar TDAVB anterior")

    # ================================================================
    # UTILIDAD (debug / web)
    # ================================================================
    def get_estado(self) -> dict:
        return {
            "tdavb_anterior_seg": self._tdavb_anterior,
            "tiempo_acumulado_hoy_seg": self._tiempo_acumulado_hoy,
            "tdavb_para_dosificacion_seg": self.tiempoDiarioApertura(),
            "valvula_abierta": self._esta_abierta
        }
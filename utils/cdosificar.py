# cdosificar.py
from typing import Optional
from interfaces import IValvulaListener, INuevoDia, ITick
from cbomba_farmaco import CBombaFarmaco
from cparametros_operativos import CParametrosOperativos
from ctdavb import CTDAVB

class CDosificar(IValvulaListener, INuevoDia, ITick):
    """
    Clase responsable de controlar la bomba dosificadora según:
      - Cantidad diaria de remedio (carga × dosis)
      - TDAVB contraído (del día anterior)
      - Caudal de la bomba
    Detiene la dosificación cuando se alcanza el máximo diario aunque siga entrando agua.
    """

    def __init__(self,
                 bomba: CBombaFarmaco,
                 parametros: CParametrosOperativos,
                 ctdavb: CTDAVB) -> None:
        """
        Constructor según documento + referencia a CTDAVB (necesaria para obtener
        el tiempo de dosificación objetivo).
        """
        self._bomba = bomba
        self._parametros = parametros
        self._ctdavb = ctdavb

        # Estado interno
        self._remedio_acumulado_hoy: float = 0.0      # ml dosificados hoy
        self._valvula_abierta: bool = False
        self._dosing_active: bool = True              # se desactiva al llegar al máximo diario
        self._pump_accumulator: float = 0.0           # acumulador para dosificación precisa

        print("✅ CDosificar iniciada")

    # ================================================================
    # MÉTODOS INTERNOS
    # ================================================================
    def _calcular_dosis_diaria_ml(self) -> float:
        """Cantidad total de remedio que hay que dosificar hoy (ml)."""
        carga = self._parametros.get_Carga()
        dosis_por_100kg = self._parametros.get_DosisDiariaFarmaco()
        return (carga / 100.0) * dosis_por_100kg

    def _calcular_tdavb_contraction(self) -> int:
        """TDAVB a usar para calcular la tasa de dosificación."""
        return self._ctdavb.tiempoDiarioApertura()

    # ================================================================
    # INTERFACES IMPLEMENTADAS
    # ================================================================
    def avisoCambioEstadoVB(self, estado: bool) -> None:
        """La válvula abrió o cerró."""
        self._valvula_abierta = estado

        if not estado:
            # Al cerrar la válvula siempre apagamos la bomba
            self._bomba.apagar()

    def avisoNuevoDia(self) -> None:
        """00:00 → reseteamos todo para el nuevo día."""
        self._remedio_acumulado_hoy = 0.0
        self._pump_accumulator = 0.0
        self._dosing_active = True
        print("[Dosificar] Nuevo día - acumulado reseteado a 0 ml")

    def tick(self, cadencia: int) -> None:
        """
        Llamado cada segundo.
        Aquí se decide si encender o apagar la bomba según la tasa calculada.
        """
        if not self._dosing_active:
            self._bomba.apagar()
            return

        # Verificamos si ya llegamos al máximo diario
        target_diario_ml = self._calcular_dosis_diaria_ml()
        if self._remedio_acumulado_hoy >= target_diario_ml:
            self._dosing_active = False
            self._bomba.apagar()
            print(f"[Dosificar] ⚠️  Máximo diario alcanzado ({self._remedio_acumulado_hoy:.1f} ml)")
            return

        if self._valvula_abierta:
            tdavb_contraction = self._calcular_tdavb_contraction()

            if tdavb_contraction <= 0:
                self._bomba.apagar()
                return

            # ml que deberíamos dosificar por cada segundo que la válvula está abierta
            ml_por_segundo_valvula = target_diario_ml / tdavb_contraction

            # Acumulamos lo que "debemos" dosificar este segundo
            self._pump_accumulator += ml_por_segundo_valvula

            q_bomba = self._parametros.get_QBomba()

            # Si el acumulador alcanzó el caudal de la bomba → encendemos 1 segundo
            if self._pump_accumulator >= q_bomba:
                self._bomba.encender()
                self._pump_accumulator -= q_bomba
                self._remedio_acumulado_hoy += q_bomba
            else:
                self._bomba.apagar()
        else:
            # Válvula cerrada → bomba siempre apagada
            self._bomba.apagar()

    def remedioAcumulado(self) -> float:
        """Retorna ml de remedio dosificados desde las 00:00 de hoy."""
        return round(self._remedio_acumulado_hoy, 2)

    # ================================================================
    # MÉTODO DE UTILIDAD (debug / web)
    # ================================================================
    def get_estado(self) -> dict:
        """Información completa para depuración o interfaz web."""
        target = self._calcular_dosis_diaria_ml()
        return {
            "remedio_acumulado_hoy_ml": self.remedioAcumulado(),
            "dosis_diaria_objetivo_ml": round(target, 2),
            "porcentaje_dosificado": round((self._remedio_acumulado_hoy / target * 100), 1) if target > 0 else 0,
            "dosing_active": self._dosing_active,
            "valvula_abierta": self._valvula_abierta,
            "pump_accumulator": round(self._pump_accumulator, 3)
        }
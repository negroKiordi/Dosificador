# utils/cdosificar.py
from typing import Optional
from utils.interfaces import IValvulaListener, INuevoDia, ITick
from utils.cbomba_farmaco import CBombaFarmaco
from utils.cparametros_operativos import CParametrosOperativos
from utils.ctdavb import CTDAVB

class CDosificar(IValvulaListener, INuevoDia, ITick):
    """
    Solo indica a la bomba cuántos ml dosificar.
    Acumula el valor REAL retornado por bomba.dosificar().
    """

    def __init__(self,
                 bomba: CBombaFarmaco,
                 parametros: CParametrosOperativos,
                 ctdavb: CTDAVB) -> None:
        self._bomba = bomba
        self._parametros = parametros
        self._ctdavb = ctdavb

        self._remedio_acumulado_hoy: float = 0.0
        self._valvula_abierta: bool = False
        self._dosing_active: bool = True

        print("✅ CDosificar iniciada (usa bomba.dosificar() y acumula el valor real retornado)")

    def _calcular_dosis_diaria_ml(self) -> float:
        carga = self._parametros.get_Carga()
        dosis_por_100kg = self._parametros.get_DosisDiariaFarmaco()
        return (carga / 100.0) * dosis_por_100kg

    def avisoCambioEstadoVB(self, estado: bool) -> None:
        self._valvula_abierta = estado

    def avisoNuevoDia(self) -> None:
        self._remedio_acumulado_hoy = 0.0
        self._dosing_active = True
        print("[Dosificar] Nuevo día - acumulado reseteado")

    def tick(self, cadencia: int) -> None:
        if not self._dosing_active:
            return

        target_diario = self._calcular_dosis_diaria_ml()
        if self._remedio_acumulado_hoy >= target_diario:
            self._dosing_active = False
            print(f"[Dosificar] ⚠️ Máximo diario alcanzado ({self._remedio_acumulado_hoy:.1f} ml)")
            return

        if self._valvula_abierta:
            tdavb_contraction = self._ctdavb.tiempoDiarioApertura()
            if tdavb_contraction <= 0:
                return

            ml_por_segundo_valvula = target_diario / tdavb_contraction
            ml_this_tick = ml_por_segundo_valvula * cadencia

            # ←←← AQUÍ SE USA EL VALOR RETORNADO POR DOSIFICAR
            volumen_real_dosificado = self._bomba.dosificar(ml_this_tick)
            self._remedio_acumulado_hoy += volumen_real_dosificado

    def remedioAcumulado(self) -> float:
        return round(self._remedio_acumulado_hoy, 2)

    def get_estado(self) -> dict:
        target = self._calcular_dosis_diaria_ml()
        return {
            "remedio_acumulado_hoy_ml": self.remedioAcumulado(),
            "dosis_diaria_objetivo_ml": round(target, 2),
            "porcentaje_dosificado": round((self._remedio_acumulado_hoy / target * 100), 1) if target > 0 else 0,
            "dosing_active": self._dosing_active,
            "valvula_abierta": self._valvula_abierta
        }
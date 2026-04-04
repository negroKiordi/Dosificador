# utils/cdosificar.py
from utils.interfaces import IValvulaListener, INuevoDia, ITick
from utils.cbomba_farmaco import CBombaFarmaco
from utils.cparametros_operativos import CParametrosOperativos
from utils.ctdavb import CTDAVB

class CDosificar(IValvulaListener, INuevoDia, ITick):
    """
    Controla la dosificación según la nueva lógica que pediste.
    Ya no calcula ml por segundo, sino que dosifica solo si el acumulado
    está por debajo del proporcional al tiempo de apertura actual.
    """

    def __init__(self, bomba, parametros, ctdavb):
        self._bomba = bomba
        self._parametros = parametros
        self._ctdavb = ctdavb

        self._estadoOperativo = True # True = operativo, False = Estado latente para operación manual de bomba
        self._remedio_acumulado_hoy = 0.0
        self._valvula_abierta = False
        self._dosing_active = True
        self._dosis_anterior = self._calcular_dosis_diaria_ml()  # Para detectar cambios en la dosis diaria

        print("✅ CDosificar iniciada (nueva lógica de dosificación proporcional)")

    def _calcular_dosis_diaria_ml(self):
        """Cantidad total de remedio que hay que dosificar hoy (ml)."""
        carga = self._parametros.get_Carga()
        dosis_por_100kg = self._parametros.get_DosisDiariaFarmaco()
        return (carga / 100.0) * dosis_por_100kg

    # ================================================================
    # INTERFACES IMPLEMENTADAS
    # ================================================================
    def avisoCambioEstadoVB(self, estado):
        """La válvula abrió o cerró."""
        self._valvula_abierta = estado

    def avisoNuevoDia(self):
        """00:00 → reseteamos todo para el nuevo día."""
        self._remedio_acumulado_hoy = 0.0
        self._dosing_active = True
        print("[Dosificar] Nuevo día - acumulado reseteado a 0 ml")

    def tick(self):
        """
        Nueva lógica de dosificación que implementaste.
        Dosifica solo si el acumulado está por debajo del proporcional al TDAVB.
        """
        if not self._dosing_active:
            return

        target_diario = self._calcular_dosis_diaria_ml()

        # Si ya llegamos al máximo diario → apagamos la dosificación
        if self._remedio_acumulado_hoy >= target_diario:
            self._dosing_active = False
            print("[Dosificar] ⚠️ Máximo diario alcanzado (", round(self._remedio_acumulado_hoy, 1), "ml)")
            return

        if self._valvula_abierta:
            tdavb_contraction = self._ctdavb.tiempoDiarioApertura()
            if tdavb_contraction <= 0:
                return

            # Nueva condición que pediste:
            # Dosifico solo si el acumulado es MENOR al proporcional  tiempo transcurrido
            proporcion_actual = self._remedio_acumulado_hoy / target_diario if target_diario > 0 else 0
            if self._remedio_acumulado_hoy >= (target_diario * (self._ctdavb.tiempoAperturaAcumulado() / tdavb_contraction)):
                return

            print("remedio_acumulado_hoy:", round(self._remedio_acumulado_hoy, 1), 
                  "ml | target_diario:", round(target_diario, 1), 
                  "ml | proporcion_actual:", round(proporcion_actual*100, 1), "%")
            print("Proporcion temporal actual:", round((self._ctdavb.tiempoAperturaAcumulado() / tdavb_contraction) * 100, 1), 
                  "% del tiempo de apertura total")

            if self._estadoOperativo:
                # Llamamos a dosificar() y acumulamos el volumen REAL que retorna
                ml_real_dosificado = self._bomba.dosificar()
                self._remedio_acumulado_hoy += ml_real_dosificado
            else:
                print("[Dosificar] Estado latente - no se dosifica automáticamente")

    # ================================================================
    # MÉTODO DE CONSULTA Y CONFIGURACIÓN 
    # ================================================================

    def remedioAcumulado(self):
        """Retorna ml de remedio dosificados desde las 00:00 de hoy."""
        return round(self._remedio_acumulado_hoy, 2)

    def set_estado_operativo(self):
        """Cambia el estado a operativo"""
        self._estadoOperativo = True

    def set_estado_latente(self):
        """Cambia el estado a latente (para operación manual de bomba)"""
        self._estadoOperativo = False
    
    def get_estado_operativo(self):
        """Retorna el estado operativo actual"""
        return self._estadoOperativo
    
    def avisoCambioDosisDiaria(self):
        """Llamar a este método si se cambia la dosis diaria.
            El sistema calcula el porcentaje de fármaco entregado y 
            se prepara para completar el porcentaje faltante usando la nueva dosis."""
        proporcionDeCambio = self._parametros.get_DosisDiariaFarmaco() / self._dosis_anterior if self._dosis_anterior > 0 else 1

        target_diario = self._calcular_dosis_diaria_ml()
        target_diario_anterior = target_diario / proporcionDeCambio

        #Proporcentaje de remedio entregado hasta ahora con la dosis anterior
        PorcentajeDosificado = self._remedio_acumulado_hoy / target_diario_anterior if target_diario_anterior > 0 else 0
        
        #Recalculo la cantidad de remedio como si se usara la nueva dosis desde el principio del día, para mantener el mismo porcentaje de dosificación
        self._remedio_acumulado_hoy = target_diario * PorcentajeDosificado

        print("[Dosificar] Dosis diaria cambiada. Proporción actual:", round(PorcentajeDosificado*100, 1), "%")


    # ================================================================
    # MÉTODO DE UTILIDAD (debug / web)
    # ================================================================
    def get_estado(self):
        target = self._calcular_dosis_diaria_ml()
        return {
            "remedio_acumulado_hoy_ml": self.remedioAcumulado(),
            "dosis_diaria_objetivo_ml": round(target, 2),
            "porcentaje_dosificado": round((self._remedio_acumulado_hoy / target * 100), 1) if target > 0 else 0,
            "dosing_active": self._dosing_active,
            "valvula_abierta": self._valvula_abierta
        }
    

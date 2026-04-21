# utils/cdosificar.py
from utils.interfaces import IValvulaListener, INuevoDia, ITick
from utils.cbomba_farmaco import CBombaFarmaco
from utils.cparametros_operativos import CParametrosOperativos
from utils.ctdavb import CTDAVB
from utils.datalog import avisoEvento
from utils.ceventos import Eventos



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
        self._bomba_atrasada = False
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
        """La válvula abrió o cerró.
        Solo actualiza su variable self.valvula_abierta para que
        luego lo procese tick()
        """
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

        self._target_diario = self._calcular_dosis_diaria_ml()
        if self._target_diario <= 0:
            return

        self._tdavb = self._ctdavb.tiempoDiarioApertura()
        if self._tdavb <= 0:
            return
        
        # Dosifico solo si el remedio Acumulado es MENOR al Requerido.
        _remedio_requerido = (self._target_diario * 
                             (self._ctdavb.tiempoAperturaAcumulado() / 
                              self._tdavb))
        
        if self._remedio_acumulado_hoy >= self._remedio_requerido:
            # No hace falta entregar más remedio.
            if self._bomba_atrasada:
                # Si la bomba estaba atrasada pero ya alcanzamos el remedio requerido, 
                # entonces se normaliza la situación.
                self._bomba_atrasada = False
                avisoEvento(Eventos.BOMBA_RECUPERADA)
                print("[Dosificar] Situación de bomba atrasada se ha normalizado.")
            return

        # Es necesario entregar más remedio.
        if self._valvula_abierta:
            # Está entrando agua. Debo dosificar.
            if self._estadoOperativo:
                # Estado operativo funcionando. NO está en control manual.
                # Debo dosificar, estoy atrasado con el remedio.
                # Llamamos a bomba.dosificar() y acumulamos el volumen REAL
                # que retorna
                
                self._pulso_remedio = self._bomba.dosificar()

                if self._pulso_remedio > 0:

                    self._remedio_acumulado_hoy += self._pulso_remedio
                
                    _proporcion_actual = self._remedio_acumulado_hoy / self._target_diario
                    print("remedio_acumulado_hoy:", round(self._remedio_acumulado_hoy, 1), 
                          "ml | proporcion_actual:", round(self._proporcion_actual*100, 1), 
                          "%")
                    print("Proporcion temporal actual:", 
                          round((self._ctdavb.tiempoAperturaAcumulado() / self._tdavb) * 100, 1), 
                          "% del tiempo de apertura total")
                    
                    # Si ya llegamos al máximo diario → apagamos la dosificación
                    if self._remedio_acumulado_hoy >= self._target_diario:
                        self._dosing_active = False
                        avisoEvento(Eventos.DOSIS_COMPLETADA)
                        print("[Dosificar] ⚠️ Máximo diario alcanzado (", 
                            round(self._remedio_acumulado_hoy, 1), "ml)")
            else:
                # Debo dosificar pero Estado es Latente.
                # ??? Es probable que la bomba se atrase.
                # Pensar como manejar esta situación para no generar
                # Eventos Operativos de Atraso falsos debido
                # a injerencia humana.
                pass
        else:
            # Debo dosificar pero Valvula está cerrada.
            # Esto significa que la bomba no alcanza a seguir el ritmo
            # de apertura de la válvula. Esto es MALO.
            if not self._bomba_atrasada:

                self._bomba_atrasada = True
                _proporcion_actual = self._remedio_acumulado_hoy / self._target_diario
                print("Remedio_requerido:", round(self._remedio_requerido, 1), 
                    "ml | remedio_acumulado:", round(self._remedio_acumulado_hoy, 1), 
                        "ml | proporcion_actual:", round(self._proporcion_actual*100, 1), 
                        "%")
                print("Proporcion temporal actual:", 
                        round((self._ctdavb.tiempoAperturaAcumulado() / self.tdavb) * 100, 1), 
                        "% del tiempo de apertura diario")
                avisoEvento(Eventos.BOMBA_ATRASADA)


    # ================================================================
    # MÉTODO DE CONSULTA Y CONFIGURACIÓN 
    # ================================================================

    def remedioAcumulado(self):
        """Retorna ml de remedio dosificados desde las 00:00 de hoy."""
        return round(self._remedio_acumulado_hoy, 2)

    def remedioAcumuladoPorcentaje(self):
        """Retorna el porcentaje del remedio dosificado respecto a la dosis diaria."""
        target_diario = self._calcular_dosis_diaria_ml()
        return round((self._remedio_acumulado_hoy / target_diario * 100), 1) if target_diario > 0 else 0

    def set_estado_operativo(self):
        """Cambia el estado a operativo"""
        self._estadoOperativo = True
        print("[Dosificar] Pasa a Estado Operativo - se reanuda la dosificación")

    def set_estado_latente(self):
        """Cambia el estado a latente (para operación manual de bomba)"""
        self._estadoOperativo = False
        print("[Dosificar] Pasa a Estado latente - no se dosifica automáticamente")
    
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

        # Proporcentaje de remedio entregado hasta ahora con la dosis anterior
        PorcentajeDosificado = self._remedio_acumulado_hoy / target_diario_anterior if target_diario_anterior > 0 else 1
        
        # Recalculo la cantidad de remedio como si se usara la nueva dosis desde 
        # el principio del día, para mantener el mismo porcentaje de dosificación
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
    

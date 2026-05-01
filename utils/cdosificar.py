# utils/cdosificar.py
from utils.interfaces import IValvulaListener, INuevoDia, ITick
from utils.cbomba_farmaco import CBombaFarmaco
from utils.cparametros_operativos import CParametrosOperativos
from utils.ctdavb import CTDAVB
from utils.datalog import avisoEvento
from utils.ceventos import Eventos
import config
import ujson

# Archivo para persistir datos
ARCHIVO = config.ARCHIVO_PERSISTENCIA


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

        print("\n✅ [CDosificar]")
        self._estadoOperativo = True # True = operativo, False = Estado latente para operación manual de bomba
        self._load_remedio_acumulado_hoy()
        self._ticks_desde_ultima_guarda = 0
        self._bomba_atrasada = False
        self._valvula_abierta = False
        self._dosing_active = True
        self._target_diario = self._calcular_dosis_diaria_ml()  


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
        self._save_remedio_acumulado_hoy()
        self._dosing_active = True
        print("[Dosificar] Nuevo día - acumulado reseteado a 0 ml")

    def tick(self):
        """
        Nueva lógica de dosificación que implementaste.
        Dosifica solo si el acumulado está por debajo del proporcional al TDAVB.
        """
        self._ticks_desde_ultima_guarda += 1

        if not self._dosing_active:
            return

        if self._target_diario <= 0:
            return

        self._tdavb = self._ctdavb.tiempoDiarioApertura()
        if self._tdavb <= 0:
            return
        
        # Dosifico solo si el remedio Acumulado es MENOR al Requerido.
        self._remedio_requerido = (self._target_diario * (self._ctdavb.tiempoAperturaAcumulado() / self._tdavb))
        
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
                                    
                    print("remedio_acumulado_hoy:", self.remedioAcumulado(), 
                          "ml | proporcion_actual:", self.remedioAcumuladoPorcentaje(), 
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

                    # Guardamos el remedio acumulado cada T_PERSISTENCIA segundos para no perder mucha información en caso de corte de energía.          
                    if self._ticks_desde_ultima_guarda >= config.T_PERSISTENCIA:
                        self._save_remedio_acumulado_hoy()  # Guardamos el remedio_acumulado_hoy actual para persistir el valor en caso de corte de energía.
                        self._ticks_desde_ultima_guarda = 0
                        print("[CDosificar] Guardando remedio acumulado hoy:", self._remedio_acumulado_hoy, "ml") 
                    

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
                print("[Dosificar] ⚠️ Bomba atrasada - no se está dosificando lo suficiente para seguir el ritmo de apertura de la válvula.")
                print(self.get_estado())
                avisoEvento(Eventos.BOMBA_ATRASADA) 
 


    
    # ================================================================
    # PERSISTENCIA de la información del CDosificar
    # ================================================================
    def _load_remedio_acumulado_hoy(self):
        try:
            with open(ARCHIVO, "r") as f:
                datos = ujson.load(f)
                self._remedio_acumulado_hoy = datos["remedio_dosificado"]
                print("[CDosificar] Remedio acumulado hoy cargado:", self._remedio_acumulado_hoy, "ml")
        except (OSError, ValueError):
            self._remedio_acumulado_hoy = 0
            print("[CDosificar] No se pudo cargar remedio acumulado hoy, iniciando en 0 ml")

    def _save_remedio_acumulado_hoy(self):
        try:
            with open(ARCHIVO, "r") as f:
                datos = ujson.load(f)
        except (OSError, ValueError):
            print("[CDosificar] No se pudo cargar el archivo de persistencia")
            datos = {}
            
        datos["remedio_dosificado"] = self._remedio_acumulado_hoy
        try:
            with open(ARCHIVO, "w") as f:
                ujson.dump(datos, f)
        except OSError:
            print("[CDosificar] No se pudo guardar remedio acumulado hoy")   



    # ================================================================
    # MÉTODO DE CONSULTA Y CONFIGURACIÓN
    # ================================================================

    def remedioAcumulado(self):
        """Retorna ml de remedio dosificados desde las 00:00 de hoy.""" 
        return round(self._remedio_acumulado_hoy, 2)

    def remedioAcumuladoPorcentaje(self):
        """Retorna el porcentaje del remedio dosificado respecto a la dosis diaria."""
        return round((self._remedio_acumulado_hoy / self._target_diario * 100), 1) if self._target_diario > 0 else 0

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
        proporcionDeCambio = self._parametros.get_DosisDiariaFarmaco() / self._target_diario if self._target_diario > 0 else 1

        target_diario = self._calcular_dosis_diaria_ml()
        target_diario_anterior = target_diario / proporcionDeCambio

        # Proporcentaje de remedio entregado hasta ahora con la dosis anterior
        PorcentajeDosificado = self._remedio_acumulado_hoy / target_diario_anterior if target_diario_anterior > 0 else 1
        
        # Recalculo la cantidad de remedio como si se usara la nueva dosis desde 
        # el principio del día, para mantener el mismo porcentaje de dosificación
        self._remedio_acumulado_hoy = target_diario * PorcentajeDosificado

        self._target_diario = target_diario  # Actualizo el nuevo objetivo diario

        print("[Dosificar] Dosis diaria cambiada. Proporción actual:", round(PorcentajeDosificado*100, 1), "%")


    # ================================================================
    # MÉTODO DE UTILIDAD (debug / web)
    # ================================================================
    def get_estado(self):
        return {
            "remedio_acumulado_hoy_ml": self.remedioAcumulado(),
            "dosis_diaria_objetivo_ml": round(self._target_diario, 2),
            "porcentaje_dosificado": round((self._remedio_acumulado_hoy / self._target_diario * 100), 1) if self._target_diario > 0 else 0,
            "dosing_active": self._dosing_active,
            "valvula_abierta": self._valvula_abierta
        }
    

    
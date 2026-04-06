# utils/ctdavb.py
import ujson
from utils.interfaces import IValvulaListener, INuevoDia, ITick
from utils.cparametros_operativos import CParametrosOperativos
from utils.cvalvula_bebedero import CvalvulaBebedero 

# Archivo para persistir el TDAVB del día anterior
ARCHIVO_TDAVB = "tdavb_persistencia.json"

class CTDAVB(IValvulaListener, INuevoDia, ITick):
    """
    Clase Tiempo Diario de Apertura de la Válvula del Bebedero (CTDAVB).
    """

    def __init__(self, parametros):
        self._parametros = parametros
        self._valvula = None

        # Variables de estado
        self._tiempo_acumulado_hoy = 0          # segundos reales de apertura hoy
        self._tdavb = 0                         # TDAVB actual para dosificación
        self._esta_abierta = False

        self._load_tdavb()                     # Cargo configuración guardada (si existe)

        print("CTDAVB iniciada - TDAVB anterior:", self._tdavb, "segundos")

    # ================================================================
    # MÉTODOS DE CONFIGURACIÓN
    # ================================================================
    def valvulaBebedero(self, valvula):
        """Registra la válvula y sincroniza el estado inicial."""
        self._valvula = valvula
        # Sincronizamos el flag con la realidad física
        if self._valvula is not None:
            self._esta_abierta = self._valvula.valvulaAbierta()

    def actualizacionParametrosOperativos(self):
        """ Aviso de que los parámetros operativos han cambiado. 
            Por ahora solo la carga afecta al TDAVB, pero podríamos reaccionar a otros cambios en el futuro.
        """
        # Por ahora no hacemos nada con los parámetros, pero podríamos recalcular el TDAVB si la carga cambia significativamente.
        pass    



    # ================================================================
    # INTERFACES IMPLEMENTADAS
    # ================================================================
    def avisoCambioEstadoVB(self, estado):
        """Recibe notificación cuando la válvula abre o cierra."""
        self._esta_abierta = estado

    def avisoNuevoDia(self):
        """00:00 → Actualizar el TDAVB
            Si no hubo cambio de carga el TDAVB se actualiza con el valor acumulado al final del día.
            Si hubo cambio de carga se ajusta el valor actual proporcionalmente al cambio de carga.
        """

        #cambio de carga?
        if self._parametros.get_carga() != self._load_carga_anterior():
            carga_anterior = self._load_carga_anterior()
            carga_actual = self._parametros.get_Carga()
            self._save_carga_anterior(carga_actual)  # Guardamos la nueva carga para el próximo día

            if carga_anterior > 0:
                factor_ajuste = carga_actual / carga_anterior
                self._tdavb = int(self._tdavb * factor_ajuste)
                print("[CTDAVB] Cambio de carga detectado. Ajustando TDAVB con factor:", factor_ajuste)
            else:
                self._tdavb = self._tiempo_acumulado_hoy  # Si no hay carga anterior, usamos el acumulado tal cual
        else:
            self._tdavb = self._tiempo_acumulado_hoy  # Sin cambio de carga, el TDAVB es el acumulado del día

        self._save_tdavb()  # Guardamos el TDAVB del día anterior para referencia futura

        self._tiempo_acumulado_hoy = 0
        # NO tocamos el estado actual de la válvula

        # Re-sincronizamos con la realidad por si hubo glitch
        if self._valvula is not None:
            self._esta_abierta = self._valvula.valvulaAbierta()

        print("[CTDAVB] Nuevo día → TDAVB anterior guardado:", self._tdavb, "segundos")

    def tick(self):
        """Acumula tiempo solo si la válvula está realmente abierta."""
        if self._esta_abierta:
            self._tiempo_acumulado_hoy += 1

    # ================================================================
    # MÉTODOS DE CONSULTA
    # ================================================================
    def tiempoDiarioApertura(self):
        """
        Retorna en SEGUNDOS el TDAVB a utilizar para la dosificación.
        Es el valor del día anterior afectado por el porcentaje de contracción.
        """
        porcentaje = self._parametros.get_porcentajeContraccionTDAVB()
        return int(self._tdavb * porcentaje / 100)

    def tiempoAperturaAcumulado(self):
        """Retorna el tiempo real acumulado desde las 00:00 de hoy."""
        return self._tiempo_acumulado_hoy

    def tiempoAperturaAcumuladoPorcentaje(self):
        """Retorna el porcentaje del tiempo de apertura acumulado respecto al TDAVB."""
        tdavb_para_dosificacion = self.tiempoDiarioApertura()
        return round(self._tiempo_acumulado_hoy / tdavb_para_dosificacion * 100, 1) if tdavb_para_dosificacion > 0 else 0
    
    
    # ================================================================
    # PERSISTENCIA de la información del CTDAVB
    # ================================================================
    def _load_tdavb(self):
        try:
            with open(ARCHIVO_TDAVB, "r") as f:
                datos = ujson.load(f)
                self._tdavb = datos.get("tdavb", 0)
        except (OSError, ValueError):
            self._tdavb = 1000

    def _save_tdavb(self):
        try:
            with open(ARCHIVO_TDAVB, "w") as f:
                ujson.dump({"tdavb": self._tdavb}, f)
        except OSError:
            print("No se pudo guardar TDAVB anterior")

    def _load_carga_anterior(self):
        try:
            with open(ARCHIVO_TDAVB, "r") as f:
                datos = ujson.load(f)
                return datos.get("carga_anterior", 0)
        except (OSError, ValueError):
            return 0

    def _save_carga_anterior(self, carga):
        try:
            with open(ARCHIVO_TDAVB, "w") as f:
                ujson.dump({"carga_anterior": carga}, f)
        except OSError:
            print("No se pudo guardar carga anterior")  


    # ================================================================
    # UTILIDAD (debug / web)
    # ================================================================
    def get_estado(self):
        return {
            "tdavb_anterior_seg": self._tdavb_anterior,
            "tiempo_acumulado_hoy_seg": self._tiempo_acumulado_hoy,
            "tdavb_para_dosificacion_seg": self.tiempoDiarioApertura(),
            "valvula_abierta": self._esta_abierta
        }
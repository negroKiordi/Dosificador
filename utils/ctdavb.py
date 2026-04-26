# utils/ctdavb.py
import ujson
from utils.interfaces import IValvulaListener, INuevoDia, ITick
from utils.cparametros_operativos import CParametrosOperativos
from utils.cvalvula_bebedero import CvalvulaBebedero 
import config

# Archivo para persistir datos
ARCHIVO = config.ARCHIVO_PERSISTENCIA


class CTDAVB(IValvulaListener, INuevoDia, ITick):
    """
    Clase Tiempo Diario de Apertura de la Válvula del Bebedero (CTDAVB).
    Responsable de computar El Tiempo Diario de Apertura de 
    la Válvula del Bebedero
    """

    def __init__(self, parametros):
        self._parametros = parametros
        self._valvula = None

        print("\n✅ [CTDAVB]")
        
        # Variables de estado
        self._tiempo_acumulado_hoy = 0   # segundos reales de apertura hoy
        self._tdavb = 0                  # TDAVB actual para dosificación
        self._esta_abierta = False
        self._ticks_desde_ultima_guarda = 0  # En esta variable se guarda cuantos tick que pasaron desde la ultima vez que se guardó self._tiempo_acumulado_hoy en el archivo, para evitar guardar cada segundo.

        self._load_tdavb()                  # Cargo configuración guardada (si existe)
        print("[CTDAVB] TDAVB anterior cargado:", self._tdavb, "segundos")
        self._load_tiempo_acumulado_hoy()   # Cargo el tiempo acumulado de hoy (si existe)
        print("[CTDAVB] Tiempo acumulado hoy cargado:", self._tiempo_acumulado_hoy, "segundos")

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
        """Recibe notificación cuando la válvula abre o cierra.
        Solo actualiza su variable self.esta_abierta para que
        luego lo procese tick()
        """
        self._esta_abierta = estado

    def avisoNuevoDia(self):
        """00:00 → Actualizar el TDAVB
            Si no hubo cambio de carga el TDAVB se actualiza con el 
            valor acumulado al final del día.
            Si hubo cambio de carga se ajusta el valor actual 
            proporcionalmente al cambio de carga.
        """

        # cambio de carga?
        if self._parametros.get_carga() != self._load_carga_anterior():
            # Hubo cambio de Carga.
            carga_anterior = self._load_carga_anterior()
            carga_actual = self._parametros.get_Carga()
            self._save_carga_anterior(carga_actual)  # Guardamos la nueva carga

            if carga_anterior > 0:
                factor_ajuste = carga_actual / carga_anterior
                # No uso el _tiempo_acumulado_hoy porque hubo cambio de animales
                # en algún momento del día.
                self._tdavb = int(self._tdavb * factor_ajuste)
                print("[CTDAVB] Cambio de carga detectado. Ajustando TDAVB con factor:", 
                      factor_ajuste)
            else:
                # Si no hay carga anterior, usamos el acumulado tal cual.
                self._tdavb = self._tiempo_acumulado_hoy
        else:
            # Sin cambio de carga, el TDAVB es el acumulado del día
            self._tdavb = self._tiempo_acumulado_hoy  

        self._save_tdavb()  # Guardamos el TDAVB del día anterior.

        self._tiempo_acumulado_hoy = 0
        # NO tocamos el estado actual de la válvula.

        print("[CTDAVB] Nuevo día → TDAVB anterior guardado:", self._tdavb, "segundos")

    def tick(self):
        """Acumula tiempo solo si la válvula está realmente abierta."""
        self._ticks_desde_ultima_guarda += 1
        if self._esta_abierta:
            self._tiempo_acumulado_hoy += 1
            self._ticks_desde_ultima_guarda += 1
            # Guardamos el acumulado cada T_PERSISTENCIA segundos para no perder mucha información en caso de corte de energía.          
            if self._ticks_desde_ultima_guarda >= config.T_PERSISTENCIA:
                self._save_tiempo_acumulado_hoy()  # Guardamos el tiempo_acumulado_hoy actual para persistir el valor en caso de corte de energía.
                self._ticks_desde_ultima_guarda = 0
                print("[CTDAVB] Guardando tiempo acumulado hoy:", self._tiempo_acumulado_hoy, "segundos") 

    # ================================================================
    # MÉTODOS DE CONSULTA
    # ================================================================
    def tiempoDiarioApertura(self):
        """
        Retorna en SEGUNDOS el TDAVB a utilizar para la dosificación.
        Es el valor del día anterior afectado por el porcentaje de contracción.
        """
        porcentaje = self._parametros.get_porcentajeContraccionTDAVB()
        return int(self._tdavb * (1- porcentaje/100))

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
            with open(ARCHIVO, "r") as f:
                datos = ujson.load(f)
                self._tdavb = datos.get("tdavb", 0)
        except (OSError, ValueError):
            self._tdavb = 1000

    def _save_tdavb(self):
        try:
            with open(ARCHIVO, "r") as f:
                datos = ujson.load(f)
                datos["tdavb"] = self._tdavb
        except OSError:
            print("[CTDAVB] No se pudo cargar el archivo de persistencia")
            return
        try:
            with open(ARCHIVO, "w") as f:
                ujson.dump(datos, f)
        except OSError:
            print("[CTDAVB] No se pudo guardar TDAVB anterior")      


    def _load_carga_anterior(self):
        try:
            with open(ARCHIVO, "r") as f:
                datos = ujson.load(f)
                return datos.get("carga_anterior", 0)
        except (OSError, ValueError):
            return 0

    def _save_carga_anterior(self, carga):
        try:
            with open(ARCHIVO, "r") as f:
                datos = ujson.load(f)
                datos["carga_anterior"] = carga
        except OSError:
            print("[CTDAVB] No se pudo cargar el archivo de persistencia")
        try:
            with open(ARCHIVO, "w") as f:
                ujson.dump(datos, f)
        except OSError:
            print("[CTDAVB] No se pudo guardar carga anterior")      

    def _load_tiempo_acumulado_hoy(self):
        try:
            with open(ARCHIVO, "r") as f:
                datos = ujson.load(f)
                self._tiempo_acumulado_hoy = datos["t_acumulado"]
        except (OSError, ValueError):
            self._tiempo_acumulado_hoy = 0
            print("[CTDAVB] No se pudo cargar tiempo acumulado hoy, iniciando en 0 segundos")

    def _save_tiempo_acumulado_hoy(self):
        try:
            with open(ARCHIVO, "r") as f:
                datos = ujson.load(f)
        except OSError:
            print("[CTDAVB] No se pudo cargar el archivo de persistencia")
            datos = {}
    
        datos["t_acumulado"] = self._tiempo_acumulado_hoy
        try:
            with open(ARCHIVO, "w") as f:
                ujson.dump(datos, f)
        except OSError:
            print("[CTDAVB] No se pudo guardar tiempo acumulado")

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
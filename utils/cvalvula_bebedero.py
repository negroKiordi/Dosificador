# utils/valvula_bebedero.py
import machine
from utils.interfaces import IValvulaListener, ITick
from utils.datalog import avisoEvento
from utils.ceventos import Eventos

class CvalvulaBebedero(ITick):
    """
    Responsable de leer el microswitch magnético del flotante del bebedero
    y notificar cambios de estado a todos los listeners (CTDAVB y CDosificar).
    """

    def __init__(self, pin):
        """
        pin: número de GPIO donde está conectado el microswitch magnético
             (ejemplo: 5 = D1 en NodeMCU V3)
        _estado_anterior = valor actual de la valvula.
        """
        # Configuración típica para microswitch con pull-up interno
        self._pin = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
        
        # Estado anterior para detectar flancos (cambios)
        self._estado_anterior = self.valvulaAbierta()
        
        # Lista de listeners (sin typing)
        self._listeners = []

        print("ValvulaBebedero iniciada en GPIO", pin)

    def valvulaAbierta(self):
        """
        Retorna True si la válvula del bebedero está abierta
        (flotante bajo → ingreso de agua).
        """
        # == 1 porque con PULL_UP el pin está en HIGH cuando el switch está abierto.
        # Si el microswitch está cableado de forma inversa, cambia a == 0
        return self._pin.value() == 1

    def listaCambioValvula(self, aviso):
        """Agrega un listener que será notificado cuando cambie el estado."""
        if aviso not in self._listeners:
            self._listeners.append(aviso)
            print("Nuevo listener agregado a ValvulaBebedero:", 
                  aviso.__class__.__name__)

    def tick(self):
        """
        Llamado cada segundo por CTiempo.
        Lee el pin y notifica si hubo cambio de estado.
        """
        estado_actual = self.valvulaAbierta()

        # Detectamos cambio de estado
        if estado_actual != self._estado_anterior:
            # Notificamos a TODOS los listeners
            for listener in self._listeners:
                listener.avisoCambioEstadoVB(estado_actual)
            
            # Actualizamos estado anterior
            self._estado_anterior = estado_actual

            # Inserto Log
            avisoEvento(Eventos.VB_ABRE) if estado_actual else avisoEvento(Eventos.VB_CIERRA)
            
            # Debug útil durante las primeras pruebas
            print("[Valvula] Cambio detectado →", "ABIERTA" if estado_actual else "CERRADA")

        # En esta clase no usamos la cadencia,
        # pero la recibimos por la interfaz ITick
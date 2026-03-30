# valvula_bebedero.py
import machine
from interfaces import IValvulaListener, ITick
from typing import List

class ValvulaBebedero(ITick):
    """
    Responsable de leer el microswitch magnético del flotante del bebedero
    y notificar cambios de estado a todos los listeners (CTDAVB y CDosificar).
    """

    def __init__(self, pin: int) -> None:
        """
        pin: número de GPIO donde está conectado el microswitch magnético
             (ejemplo: 5 = D1 en NodeMCU V3)
        """
        # Configuración típica para microswitch con pull-up interno
        self._pin = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
        
        # Estado anterior para detectar flancos (cambios)
        self._estado_anterior: bool = False
        
        # Lista de objetos que quieren ser notificados (implementan IValvulaListener)
        self._listeners: List[IValvulaListener] = []

        print(f"ValvulaBebedero iniciada en GPIO {pin}")

    def valvulaAbierta(self) -> bool:
        """
        Retorna True si la válvula del bebedero está abierta
        (flotante bajo → ingreso de agua).
        """
        # == 0 porque con PULL_UP el pin está en HIGH cuando el switch está abierto.
        # Si tu microswitch está cableado de forma inversa, cambia a == 1
        return self._pin.value() == 0

    def listaCambioValvula(self, aviso: IValvulaListener) -> None:
        """Agrega un listener que será notificado cuando cambie el estado."""
        if aviso not in self._listeners:
            self._listeners.append(aviso)

    def tick(self, cadencia: int) -> None:
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

            # Debug útil durante las primeras pruebas
            print(f"[Valvula] Cambio detectado → {'ABIERTA' if estado_actual else 'CERRADA'}")

        # En esta clase no usamos la cadencia, pero la recibimos por la interfaz ITick
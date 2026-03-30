# cbomba_farmaco.py
import machine
from typing import Optional

class CBombaFarmaco:
    """
    Controla la bomba dosificadora de carminativo (Brouwer MAX u otra bomba peristáltica/electromagnética).
    Se conecta directamente a un pin GPIO del NodeMCU.
    """

    def __init__(self, pin: int) -> None:
        """
        pin: número de GPIO donde está conectada la bomba
             (ejemplo: 4 = D2 en NodeMCU V3)
        """
        self._pin = machine.Pin(pin, machine.Pin.OUT)
        self._pin.value(0)          # Aseguramos que la bomba arranque apagada
        self._estado_actual: bool = False

        print(f"✅ CBombaFarmaco iniciada en GPIO {pin} (inicialmente apagada)")

    def encender(self) -> None:
        """Enciende la bomba dosificadora."""
        if not self._estado_actual:
            self._pin.value(1)
            self._estado_actual = True
            print("[Bomba] 🔥 ENCENDIDA")

    def apagar(self) -> None:
        """Apaga la bomba dosificadora."""
        if self._estado_actual:
            self._pin.value(0)
            self._estado_actual = False
            print("[Bomba] ⭕ APAGADA")

    def esta_encendida(self) -> bool:
        """Retorna True si la bomba está encendida en este momento."""
        return self._estado_actual

    def toggle(self) -> None:
        """Método de conveniencia (útil durante pruebas)."""
        if self._estado_actual:
            self.apagar()
        else:
            self.encender()

    # ================================================================
    # MÉTODO EXTRA (útil para CDatalog y depuración)
    # ================================================================
    def get_estado(self) -> bool:
        """Alias de esta_encendida() para que CDatalog pueda leerlo fácilmente."""
        return self.esta_encendida()
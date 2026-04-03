# utils/cbomba_farmaco.py
import machine
from typing import Optional
from utils.interfaces import ITick
from utils.cparametros_operativos import CParametrosOperativos

class CBombaFarmaco(ITick):
    """
    Controla la bomba dosificadora.
    - Hereda ITick para manejar el tiempo de encendido internamente.
    - Método dosificar(volumen_ml) ahora RETORNA el volumen REAL que va a dosificar.
    """

    def __init__(self, pin: int, parametros: CParametrosOperativos) -> None:
        self._pin = machine.Pin(pin, machine.Pin.OUT)
        self._pin.value(0)
        self._parametros = parametros
        self._tiempo_restante_encendido: float = 0.0

        print(f"✅ CBombaFarmaco iniciada en GPIO {pin} (tiempo mín. encendido = {parametros.get_tiempoMinEncendidoBomba()} s)")

    # ================================================================
    # MÉTODO PRINCIPAL (MODIFICADO según tu solicitud)
    # ================================================================
    def dosificar(self, volumen_solicitado_ml: float) -> float:
        """
        Solicita dosificar un volumen en ml.
        Retorna el volumen REAL que se va a dosificar (teniendo en cuenta tiempo mínimo).
        """
        if volumen_solicitado_ml <= 0:
            return 0.0

        q_bomba = self._parametros.get_QBomba()
        if q_bomba <= 0:
            return 0.0

        tiempo_necesario = volumen_solicitado_ml / q_bomba
        tiempo_min = self._parametros.get_tiempoMinEncendidoBomba()
        tiempo_real = max(tiempo_necesario, tiempo_min)

        # Volumen real que se dosificará
        volumen_real_ml = tiempo_real * q_bomba

        self._tiempo_restante_encendido += tiempo_real

        # print(f"[Bomba] Solicitado {volumen_solicitado_ml:.2f} ml → REAL {volumen_real_ml:.2f} ml ({tiempo_real:.1f} s)")
        return volumen_real_ml

    # ================================================================
    # IMPLEMENTACIÓN DE ITick
    # ================================================================
    def tick(self, cadencia: int) -> None:
        if self._tiempo_restante_encendido > 0:
            self._pin.value(1)
            self._tiempo_restante_encendido -= cadencia
            if self._tiempo_restante_encendido < 0:
                self._tiempo_restante_encendido = 0
        else:
            self._pin.value(0)

    # Métodos manuales para pruebas (mantengo)
    def encender(self) -> None:
        self._tiempo_restante_encendido = 999999
        self._pin.value(1)

    def apagar(self) -> None:
        self._tiempo_restante_encendido = 0
        self._pin.value(0)

    def esta_encendida(self) -> bool:
        return self._tiempo_restante_encendido > 0
# utils/cbomba_farmaco.py 
import machine
from utils.interfaces import ITick
from utils.cparametros_operativos import CParametrosOperativos

class CBombaFarmaco(ITick):
    """
    Controla la bomba dosificadora.
    - Hereda ITick para manejar el tiempo de encendido internamente.
    - Método dosificar() ahora dosifica siempre el volumen fijo
      (q_bomba * tiempo_min_encendido_bomba).
    """

    def __init__(self, pin, parametros):
        self._pin = machine.Pin(pin, machine.Pin.OUT)
        self._pin.value(0)
        self._parametros = parametros
        self._tiempo_restante_encendido = 0.0   # segundos que aún debe estar encendida
        self._tiempo_bomba_descansando = 0.0    # segundos que aún debe descansar (para evitar sobrecalentamiento)

        print("CBombaFarmaco iniciada en GPIO", pin,
              "(tiempo mín. encendido =", parametros.get_tiempoEncendidoBomba(), "s)")

    # ================================================================
    # NUEVO MÉTODO DOSIFICAR (tal como lo escribiste)
    # ================================================================
    def dosificar(self):
        """
        Dosifica siempre el volumen fijo definido por:
        volumen = q_bomba * tiempo_min_encendido_bomba
        Retorna el volumen REAL que se va a dosificar.
        """
        q_bomba = self._parametros.get_QBomba()
        if q_bomba <= 0:
            return 0.0

        # No dosificamos si la bomba está descansando
        if self._tiempo_bomba_descansando > 0:
            print("[Bomba] En descanso")
            return 0.0  

        # No dosificamos si la bomba ya está encendida, para evitar sobrecarga
        if self._tiempo_restante_encendido > 0:
            print("[Bomba] Ya encendida")
            return 0.0  

        tiempo_encendido = self._parametros.get_tiempoEncendidoBomba()
        volumen_dosificado_ml = q_bomba * tiempo_encendido

        # Agregamos el tiempo al temporizador interno
        self._tiempo_restante_encendido += tiempo_encendido

        print("[Bomba] Dosificando", round(volumen_dosificado_ml, 2), "ml")
        return volumen_dosificado_ml

    # ================================================================
    # IMPLEMENTACIÓN DE ITick (maneja el encendido/apagado) 
    # ================================================================
    def tick(self):
        """Llamado cada segundo. Maneja el temporizador de la bomba."""
        if self._tiempo_restante_encendido > 0:
            self._pin.value(1)                    # ENCENDIDA
            self._tiempo_restante_encendido -= 1  # Reducimos 1 segundo
            if self._tiempo_restante_encendido <= 0:
                self._tiempo_restante_encendido = 0
                self._tiempo_bomba_descansando = self._parametros.get_tiempoDescansoBomba()  # Iniciamos el tiempo de descanso para evitar sobrecalentamiento
        else:
            self._pin.value(0)                    # APAGADA
            # Manejo del tiempo de descanso para evitar sobrecalentamiento
            if self._tiempo_bomba_descansando > 0:
                self._tiempo_bomba_descansando -= 1
                if self._tiempo_bomba_descansando < 0:
                    self._tiempo_bomba_descansando = 0  

    # ================================================================
    # MÉTODOS MANUALES (útiles para pruebas)
    # ================================================================
    def encender(self):
        """Enciende manualmente (solo para pruebas)."""
        self._tiempo_restante_encendido = 999999
        self._pin.value(1)

    def apagar(self):
        """Apaga manualmente (solo para pruebas)."""
        self._tiempo_restante_encendido = 0
        self._pin.value(0)

    def esta_encendida(self):
        """Retorna True si la bomba está encendida."""
        return self._tiempo_restante_encendido > 0
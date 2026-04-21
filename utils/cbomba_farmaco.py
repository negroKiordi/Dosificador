# utils/cbomba_farmaco.py 
import machine
from utils.interfaces import ITick
from utils.cparametros_operativos import CParametrosOperativos
from utils.datalog import avisoEvento
from utils.ceventos import Eventos

class CBombaFarmaco(ITick):
    """
    Controla la bomba dosificadora.
    - Hereda ITick para manejar el tiempo de encendido internamente.
    - Método dosificar() ahora dosifica siempre el volumen fijo
      (q_bomba * tiempo_encendido_bomba).
    """

    def __init__(self, pin, parametros):
        self._pin = machine.Pin(pin, machine.Pin.OUT)
        self._pin.value(0)
        self._parametros = parametros
        self._tiempo_restante_encendido = 0.0   # segundos que aún debe estar encendida
        self._tiempo_bomba_descansando = 0.0    # segundos que aún debe descansar (para evitar sobrecalentamiento)

        print("CBombaFarmaco iniciada en GPIO", pin,
              "(tiempo encendido =", parametros.get_tiempoEncendidoBomba(), "s)")

    # ================================================================
    # NUEVO MÉTODO DOSIFICAR (tal como lo escribiste)
    # ================================================================
    def dosificar(self):
        """
        Dosifica siempre el volumen fijo definido por:
        volumen = q_bomba * tiempoencendido_bomba
        NO enciende al Bomba, solo ajusta los temporizadores para garantizar la
        operación por Tiempo Fijo con un tiempo de descanso mínimo garantizado 
        entre  Pulsos de encendido.
        Retorna el volumen REAL que se va a dosificar que
        será:  CERO o la Cantidad de ml de un Pulso.
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
        
        #Bomba Parada y NO Descansando ==> la puedo encender nuevamente
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
        """Llamado cada segundo. Maneja el temporizado de la bomba."""
        if self._pin.value() == 1: 
            # La bomba está encendida
            self._tiempo_restante_encendido -= 1  # Reducimos 1 segundo
            if self._tiempo_restante_encendido <= 0: 
                # tiempo de encendido expirado
                self._tiempo_restante_encendido = 0
                self._tiempo_bomba_descansando = self._parametros.get_tiempoDescansoBomba()  # Iniciamos el tiempo de descanso para evitar sobrecalentamiento
                self._pin.value(0)  # APAGO la bomba
                avisoEvento(Eventos.BOMBA_PARA)
                print("[Bomba] Apagada")
        else:   
            # La bomba está apagada 
            if self._tiempo_bomba_descansando > 0:  
                # La bomba está descansando, reducimos el tiempo de descanso
                self._tiempo_bomba_descansando -= 1
                if self._tiempo_bomba_descansando <= 0:
                    # tiempo de descanso expirado
                    self._tiempo_bomba_descansando = 0  
            else:                                           
                # La bomba está apagada y no está descansando ==> la puedo encender.
                if self._tiempo_restante_encendido > 0: # El tiempo 
                    # de encendido es mayor a 0, la encendemos                    
                    self._pin.value(1)    # ENCENDIDA
                    print("[Bomba] Encendida")
                    avisoEvento(Eventos.BOMBA_ARRANCA) 
                

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
        # return self._tiempo_restante_encendido > 0
        return self._pin.value() == 1
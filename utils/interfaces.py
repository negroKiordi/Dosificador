# interfaces.py
from abc import ABC, abstractmethod
from typing import Optional

class IValvulaListener(ABC):
    """Interfaz para recibir cambios de estado de la válvula (abierta/cerrada)."""
    @abstractmethod
    def avisoCambioEstadoVB(self, estado: bool) -> None:
        """
        estado: True  = válvula ABIERTA (ingreso de agua al bebedero)
                False = válvula CERRADA
        """
        raise NotImplementedError


class INuevoDia(ABC):
    """Interfaz para recibir notificación de medianoche (00:00)."""
    @abstractmethod
    def avisoNuevoDia(self) -> None:
        raise NotImplementedError


class ITick(ABC):
    """Interfaz para recibir ticks cada segundo (orquestado por CTiempo)."""
    @abstractmethod
    def tick(self, cadencia: int) -> None:
        """cadencia = segundos entre ticks (configurado en CParametrosOperativos)"""
        raise NotImplementedError
# interfaces.py - Versión ultra-ligera para ESP8266

class IValvulaListener:
    def avisoCambioEstadoVB(self, estado):
        raise NotImplementedError


class INuevoDia:
    def avisoNuevoDia(self):
        raise NotImplementedError


class ITick:
    def tick(self):
        raise NotImplementedError
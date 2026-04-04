# utils/ctiempo.py
import machine
from utils.interfaces import INuevoDia, ITick

# ================================================================
# CLASE DS3231 (driver mínimo y compatible con MicroPython)
# ================================================================
class DS3231:
    """Driver simple para el RTC DS3231 (y también compatible con DS1307)."""

    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = 0x68

    def _bcd_to_dec(self, bcd):
        """Convierte BCD a decimal."""
        return (bcd & 0x0F) + ((bcd >> 4) * 10)

    def _dec_to_bcd(self, dec):
        """Convierte decimal a BCD."""
        return ((dec // 10) << 4) | (dec % 10)

    def get_datetime(self):
        """Lee fecha y hora del RTC. Retorna (year, month, day, hour, minute, second)"""
        data = self.i2c.readfrom_mem(self.addr, 0x00, 7)
        second = self._bcd_to_dec(data[0])
        minute = self._bcd_to_dec(data[1])
        hour   = self._bcd_to_dec(data[2] & 0x3F)   # 24h
        day    = self._bcd_to_dec(data[4])
        month  = self._bcd_to_dec(data[5])
        year   = self._bcd_to_dec(data[6]) + 2000
        return (year, month, day, hour, minute, second)

    def set_datetime(self, year, month, day, hour, minute, second):
        """Configura la fecha y hora del RTC."""
        data = bytes([
            self._dec_to_bcd(second),
            self._dec_to_bcd(minute),
            self._dec_to_bcd(hour),
            1,                                      # día de la semana (no se usa)
            self._dec_to_bcd(day),
            self._dec_to_bcd(month),
            self._dec_to_bcd(year % 100)
        ])
        self.i2c.writeto_mem(self.addr, 0x00, data)
        print("DS3231 - Fecha/hora configurada:", day, "-", month, "-", year,
              hour, ":", minute, ":", second)


# ================================================================
# CLASE CTIEMPO
# ================================================================
class CTiempo:
    """
    Orquestador de tiempo y notificaciones.
    Usa el RTC DS3231 (o DS1307) vía I2C.
    """

    def __init__(self, sda_pin, scl_pin, parametros):
        self.i2c = machine.I2C(sda=machine.Pin(sda_pin),
                               scl=machine.Pin(scl_pin),
                               freq=400000)
        self.ds3231 = DS3231(self.i2c)

        self._parametros = parametros
        self._nuevo_dia_listeners = []
        self._tick_listeners = []

        # Para detectar cambio de día
        self._ultima_fecha = self.fecha()

        print("CTiempo iniciado con RTC en I2C (SDA=", sda_pin, "SCL=", scl_pin, ")")

    def fecha(self):
        """Retorna fecha en formato dd-mm-yyyy"""
        y, m, d, _, _, _ = self.ds3231.get_datetime()
        return "{:02d}-{:02d}-{}".format(d, m, y)

    def hora(self):
        """Retorna hora en formato hh:mm:ss"""
        _, _, _, h, m, s = self.ds3231.get_datetime()
        return "{:02d}:{:02d}:{:02d}".format(h, m, s)

    def listaNuevoDia(self, aviso):
        """Agrega listener para nuevo día (00:00)."""
        if aviso not in self._nuevo_dia_listeners:
            self._nuevo_dia_listeners.append(aviso)
            print("CTiempo - Nuevo listener de nuevo día agregado:", aviso.__class__.__name__)
            return True
        return False

    def listaTick(self, aviso):
        """Agrega listener para recibir tick cada segundo."""
        if aviso not in self._tick_listeners:
            self._tick_listeners.append(aviso)
            print("CTiempo - Nuevo listener de tick agregado:", aviso.__class__.__name__)
            return True
        return False

    def procesar_tick(self):
        """Llama a todos los listeners de tick y detecta cambio de día."""
        # Notificar tick a todos
        for listener in self._tick_listeners:
            listener.tick()

        # Detectar si cambió el día
        fecha_actual = self.fecha()
        if fecha_actual != self._ultima_fecha:
            print("[CTiempo] ¡Nuevo día detectado!", fecha_actual)
            for listener in self._nuevo_dia_listeners:
                listener.avisoNuevoDia()
            self._ultima_fecha = fecha_actual

    def set_datetime(self, year, month, day, hour, minute, second):
        """Método para configurar manualmente el RTC."""
        self.ds3231.set_datetime(year, month, day, hour, minute, second)
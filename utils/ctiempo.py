# ctiempo.py
import machine
from interfaces import INuevoDia, ITick
from typing import List

# ================================================================
# CLASE DS3231 (implementación estándar mínima para MicroPython)
# ================================================================
class DS3231:
    """Driver simple y funcional para el RTC DS3231 vía I2C."""
    def __init__(self, i2c: machine.I2C):
        self.i2c = i2c
        self.addr = 0x68

    def _bcd_to_dec(self, bcd: int) -> int:
        """Convierte BCD a decimal."""
        return (bcd & 0x0F) + ((bcd >> 4) * 10)

    def _dec_to_bcd(self, dec: int) -> int:
        """Convierte decimal a BCD."""
        return ((dec // 10) << 4) | (dec % 10)

    def get_datetime(self) -> tuple:
        """Lee fecha y hora del DS3231. Retorna (year, month, day, hour, minute, second)"""
        data = self.i2c.readfrom_mem(self.addr, 0x00, 7)
        second = self._bcd_to_dec(data[0])
        minute = self._bcd_to_dec(data[1])
        hour   = self._bcd_to_dec(data[2] & 0x3F)   # formato 24h
        day    = self._bcd_to_dec(data[4])
        month  = self._bcd_to_dec(data[5])
        year   = self._bcd_to_dec(data[6]) + 2000
        return (year, month, day, hour, minute, second)

    # ================================================================
    # FUNCIÓN QUE PEDISTE (agregada ahora)
    # ================================================================
    def set_datetime(self, year: int, month: int, day: int,
                     hour: int, minute: int, second: int) -> None:
        """
        Configura la fecha y hora del RTC DS3231.
        - year: 2000-2099 (se guarda como 00-99)
        - month: 1-12
        - day: 1-31
        - hour: 0-23
        - minute: 0-59
        - second: 0-59
        """
        # Convertimos todo a BCD y armamos los 7 bytes
        data = bytes([
            self._dec_to_bcd(second),           # registro 0x00
            self._dec_to_bcd(minute),           # 0x01
            self._dec_to_bcd(hour),             # 0x02 (24h)
            1,                                  # 0x03 día de la semana (dummy, no importa)
            self._dec_to_bcd(day),              # 0x04
            self._dec_to_bcd(month),            # 0x05
            self._dec_to_bcd(year % 100)        # 0x06 (solo los últimos 2 dígitos)
        ])
        
        # Escribimos los 7 registros de una sola vez
        self.i2c.writeto_mem(self.addr, 0x00, data)
        
        print(f"[DS3231] Fecha/hora configurada: {day:02d}-{month:02d}-{year} {hour:02d}:{minute:02d}:{second:02d}")

# ================================================================
# CLASE CTIEMPO (la que pediste)
# ================================================================
class CTiempo:
    """
    Orquestador de tiempo y notificaciones.
    - Usa el DS3231 conectado por I2C.
    - Es singleton en la práctica (solo una instancia).
    - Cumple exactamente la interfaz del documento.
    """

    def __init__(self, sda_pin: int, scl_pin: int) -> None:
        """
        sda_pin: GPIO para SDA del DS3231 (ej: 14 = D5)
        scl_pin: GPIO para SCL del DS3231 (ej: 12 = D6)
        """
        self.i2c = machine.I2C(
            0,
            sda=machine.Pin(sda_pin),
            scl=machine.Pin(scl_pin),
            freq=400_000
        )
        self.ds3231 = DS3231(self.i2c)

        self._nuevo_dia_listeners: List[INuevoDia] = []
        self._tick_listeners: List[ITick] = []

        # Para detectar cambio de día
        self._ultima_fecha = self.fecha()

        print(f"✅ CTiempo iniciado con DS3231 en I2C (SDA={sda_pin}, SCL={scl_pin})")

    # ----------------------------------------------------------------
    # INTERFAZ del documento
    # ----------------------------------------------------------------
    def fecha(self) -> str:
        """Retorna fecha en formato dd-mm-yyyy"""
        y, m, d, _, _, _ = self.ds3231.get_datetime()
        return f"{d:02d}-{m:02d}-{y}"

    def hora(self) -> str:
        """Retorna hora en formato hh:mm:ss"""
        _, _, _, h, m, s = self.ds3231.get_datetime()
        return f"{h:02d}:{m:02d}:{s:02d}"

    def listaNuevoDia(self, aviso: INuevoDia) -> bool:
        """Agrega listener para nuevo día (00:00)."""
        if aviso not in self._nuevo_dia_listeners:
            self._nuevo_dia_listeners.append(aviso)
            return True
        return False

    def listaTick(self, aviso: ITick) -> bool:
        """Agrega listener para recibir tick cada segundo."""
        if aviso not in self._tick_listeners:
            self._tick_listeners.append(aviso)
            return True
        return False

    # ----------------------------------------------------------------
    # Método que se llama desde main (cada segundo)
    # ----------------------------------------------------------------
    def procesar_tick(self) -> None:
        """Llama a todos los listeners de tick y detecta cambio de día."""
        # 1. Notificar tick a todos (cadencia = 1 segundo)
        for listener in self._tick_listeners:
            listener.tick(1)

        # 2. Detectar si cambió el día
        fecha_actual = self.fecha()
        if fecha_actual != self._ultima_fecha:
            print(f"[CTiempo] ¡Nuevo día detectado! {fecha_actual}")
            for listener in self._nuevo_dia_listeners:
                listener.avisoNuevoDia()
            self._ultima_fecha = fecha_actual

    # ================================================================
    # MÉTODO PÚBLICO para setear la hora (opcional pero muy útil)
    # ================================================================
    def set_datetime(self, year: int, month: int, day: int,
                     hour: int, minute: int, second: int) -> None:
        """Método cómodo para configurar el RTC desde cualquier parte del código."""
        self.ds3231.set_datetime(year, month, day, hour, minute, second)
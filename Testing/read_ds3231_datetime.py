# read_ds3231_datetime.py
# Requiere: ds3231.py (la clase DS3231 que enviaste) en el mismo directorio

from machine import Pin, I2C
from utils.ctiempo import DS3231
import config

# Configura I2C (ajusta pines si usas otros)
i2c = I2C(scl=Pin(config.TIEMPO_SCL_PIN), sda=Pin(config.TIEMPO_SDA_PIN), freq=400000)

# Inicializa RTC
rtc = DS3231(i2c)

# Lee fecha/hora
year, month, day, hour, minute, second = rtc.get_datetime()
print("Hora en DS3231:", year, "-", month, "-", day, " ", hour, ":", minute, ":", second, sep="")

# Opcional: formato legible
print("Fecha y hora actuales:", "{:02d}-{:02d}-{:04d} {:02d}:{:02d}:{:02d}".format(day, month, year, hour, minute, second))
print("ordenable:", "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(year, month, day, hour, minute, second))

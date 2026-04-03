# set_ds3231_datetime.py
# Requiere: ds3231.py (la clase DS3231 que enviaste) en el mismo directorio

from machine import Pin, I2C
from utils.ctiempo import DS3231
import config

# Configura I2C (ajusta pines si usas otros)
i2c = I2C(scl=Pin(config.SCL_PIN), sda=Pin(config.SDA_PIN), freq=400000)

# Inicializa RTC
rtc = DS3231(i2c)

# Verificar si el DS3231 está en el bus (opcional)
devices = i2c.scan()
print("Dispositivos I2C detectados:", devices)
if 0x68 not in devices:
    print("Advertencia: DS3231 (0x68) no detectado. Revisa conexiones.")
else:
    print("DS3231 detectado en 0x68.")

# Configura fecha/hora deseada
# Formato: set_datetime(year, month, day, hour, minute, second)
rtc.set_datetime(year=2026, month=4, day=2, hour=12, minute=34, second=56)
print("Fecha/hora configurada en DS3231 a 2026-04-02 12:34:56")
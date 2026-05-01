# set_ds3231_datetime.py
# Requiere: ds3231.py (la clase DS3231 que enviaste) en el mismo directorio

from machine import Pin, I2C
from utils.ctiempo import DS3231
import config

# Configura I2C (ajusta pines si usas otros)
i2c = I2C(scl=Pin(config.TIEMPO_SCL_PIN), sda=Pin(config.TIEMPO_SDA_PIN), freq=400000)

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
y=2026
m=5
d=1
h=15
mi=35
s=0 
rtc.set_datetime(year=y, month=m, day=d, hour=h, minute=mi, second=s)
print("Fecha y hora del DS3231 configurada a: {year}-{month}-{day} {hour}:{minute}:{second}".format(
    year=y, month=m, day=d, hour=h, minute=mi, second=s))

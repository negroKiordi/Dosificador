# config.py 
"""
Archivo de configuración central.
"""

# =============================================================================
# PINES HARDWARE MCU-ESP8266
# =============================================================================
""" 
VALVULA_PIN = 5          # GPIO5 = D1
BOMBA_PIN   = 4          # GPIO4 = D2
TIEMPO_SDA_PIN = 14      # GPIO14 = D5
TIEMPO_SCL_PIN = 12      # GPIO12 = D6
PIN_BOTON_WIFI = 13      # GPIO13 = D7 (con resistencia pull-up interna, se activa al presionar a GND)
"""

# =============================================================================
# CONFIGURACIÓN DE PINES - NodeMCU ESP-32S (ESP32-WROOM-32)
# =============================================================================

# Salidas digitales (válvula y bomba) - Pines seguros y con buen PWM
VALVULA_PIN = 15          # GPIO5  → equivalente físico cercano al D1 del ESP8266
BOMBA_PIN   = 32          # GPIO4  → equivalente físico cercano al D2 del ESP8266

# I2C para el RTC (reloj) - Usamos los pines DEFAULT recomendados del ESP32
TIEMPO_SDA_PIN = 19      # GPIO21 → Mejor pin para SDA (estándar en ESP32)
TIEMPO_SCL_PIN = 18      # GPIO22 → Mejor pin para SCL (estándar en ESP32)

# Botón WiFi (input con pull-up interna)
PIN_BOTON_WIFI = 13      # GPIO13 → Mismo número que tenías, es seguro como entrada

# Pines adicionales recomendados (por si los necesitas después)
LED_STATUS     = 2     # GPIO2  (muchas placas tienen LED integrado aquí)


# =============================================================================
# VALORES POR DEFECTO
# =============================================================================
DEFAULT_PARAMETROS = {
    "q_bomba": 1.33,                      # ml/seg.
    "tiempo_encendido_bomba": 5,          # Seg de encendido de la bomba (para evitar pulsos muy cortos).
    "tiempo_descanso_bomba": 4,           # Tiempo minimo de descanso de la bomba (para evitar sobrecalentamiento).
    "porcentaje_contraccion_tdavb": 75,   # % de contracción del TDAVB para calcular el tiempo de dosificación.
    "dosis_diaria_farmaco": 2.5,          # ml / 100 kg.
    "agua_consumida_por100Kg": 10,        # l de agua diaria minimo consumida por cada 100kg de carga.
    "carga": 16000,                       # kg del rodeo 16.000kg = 40 EV.
    "q_bebida": 120,                      # l/min de bebida, para estimar tdavb al encender.
    "carga_maxima_abrevable": 1000000,    # kg, Calculado usando los parámetros actuales.
    "q_bomba_minimo": 1.0                 # ml/seg, Calculado usando los parámetros actuales.
}


# ================================================================
# PERSISTENCIA de la información de datos operativos
# ================================================================
T_PERSISTENCIA = 60   # Periodo de guardado (en segundos)
ARCHIVO_PERSISTENCIA = "persistenciaDatos.json"

# =============================================================================
# Servidor Web y WiFi
# =============================================================================
essid = "Antiempaste"
password = "antiempaste"

# Otros
DEBUG = True
ARCHIVO_PARAMETROS = "parametros.json"
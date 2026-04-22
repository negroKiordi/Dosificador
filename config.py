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
VALVULA_PIN = 5          # GPIO5  → equivalente físico cercano al D1 del ESP8266
BOMBA_PIN   = 4          # GPIO4  → equivalente físico cercano al D2 del ESP8266

# I2C para el RTC (reloj) - Usamos los pines DEFAULT recomendados del ESP32
TIEMPO_SDA_PIN = 21      # GPIO21 → Mejor pin para SDA (estándar en ESP32)
TIEMPO_SCL_PIN = 22      # GPIO22 → Mejor pin para SCL (estándar en ESP32)

# Botón WiFi (input con pull-up interna)
PIN_BOTON_WIFI = 13      # GPIO13 → Mismo número que tenías, es seguro como entrada

# Pines adicionales recomendados (por si los necesitas después)
# LED_STATUS     = 2     # GPIO2  (muchas placas tienen LED integrado aquí)


# =============================================================================
# VALORES POR DEFECTO
# =============================================================================
DEFAULT_PARAMETROS = {
    "carga": 1000,                            # kg de peso vivo del rodeo
    "dosis_diaria_farmaco": 2.5,              # ml / 100 kg
    "q_bomba": 1.33,                          # ml/seg
    "porcentaje_contraccion_tdavb": 75,       # % de contracción del TDAVB para calcular el tiempo de dosificación  
    "tiempo_encendido_bomba": 5,               # Segundos de encendido de la bomba (para evitar pulsos muy cortos)
    "tiempo_descanso_bomba": 10               # Tiempo minimo de descanso de la bomba (para evitar sobrecalentamiento)
}

# =============================================================================
# Servidor Web y WiFi
# =============================================================================
essid = "Antiempaste"
password = "antiempaste"

# Otros
DEBUG = True
ARCHIVO_PARAMETROS = "parametros.json"
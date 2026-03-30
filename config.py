# config.py
"""
Archivo de configuración central del dosificador.
Todos los pines y valores por defecto van aquí.
"""

# =============================================================================
# PINES HARDWARE (NodeMCU V3 ESP8266)
# =============================================================================
VALVULA_PIN = 5          # GPIO5 = D1  → Microswitch magnético
BOMBA_PIN   = 4          # GPIO4 = D2  → Bomba dosificadora
TIEMPO_SDA_PIN = 14      # GPIO14 = D5 → SDA del RTC DS3231
TIEMPO_SCL_PIN = 12      # GPIO12 = D6 → SCL del RTC DS3231

# =============================================================================
# VALORES POR DEFECTO DE PARÁMETROS OPERATIVOS
# (se usan la primera vez o si no existe parametros.json)
# =============================================================================
DEFAULT_PARAMETROS = {
    "carga": 0,                          # kg de peso vivo del rodeo
    "dosis_diaria_farmaco": 2.5,         # ml / 100 kg
    "q_bomba": 1.33,                     # ml/seg (Brouwer MAX)
    "porcentaje_contraccion_tdavb": 75,  # %
    "cadencia_tick": 1                   # segundos entre ticks
}

# =============================================================================
# OTROS PARÁMETROS GLOBALES
# =============================================================================
DEBUG = True
ARCHIVO_PARAMETROS = "parametros.json"   # nombre del archivo JSON persistente
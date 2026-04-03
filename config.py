# config.py
"""
Archivo de configuración central.
"""

# =============================================================================
# PINES HARDWARE
# =============================================================================
VALVULA_PIN = 5          # GPIO5 = D1
BOMBA_PIN   = 4          # GPIO4 = D2
TIEMPO_SDA_PIN = 14      # GPIO14 = D5
TIEMPO_SCL_PIN = 12      # GPIO12 = D6

# =============================================================================
# VALORES POR DEFECTO
# =============================================================================
DEFAULT_PARAMETROS = {
    "carga": 0,                               # kg de peso vivo del rodeo
    "dosis_diaria_farmaco": 2.5,              # ml / 100 kg
    "q_bomba": 1.33,                          # ml/seg
    "porcentaje_contraccion_tdavb": 75,       # % de contracción del TDAVB para calcular el tiempo de dosificación  
    "cadencia_tick": 1,                       # segundos entre cada "tick" del sistema (para procesar eventos, actualizar estados, etc.)
    "tiempo_min_encendido_bomba": 5           # segundos mínimos para que la bomba funcione (para evitar pulsos muy cortos)
}

# Otros
DEBUG = True
ARCHIVO_PARAMETROS = "parametros.json"
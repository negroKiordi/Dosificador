# config.py
"""
Archivo de configuración central.
"""

# =============================================================================
# PINES HARDWARE
# =============================================================================
VALVULA_PIN = 5          # GPIO5 = D1  Entrada Switch Valvula
BOMBA_PIN   = 4          # GPIO4 = D2
TIEMPO_SDA_PIN = 14      # GPIO14 = D5 ¿Que es???
TIEMPO_SCL_PIN = 12      # GPIO12 = D6 ¿Que es???

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

# Otros
DEBUG = True
ARCHIVO_PARAMETROS = "parametros.json"
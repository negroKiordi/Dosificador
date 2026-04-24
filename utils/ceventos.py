# utils/eventos.py
"""
Constantes de eventos para CDatalog.
Usar siempre estos valores para evitar errores de tipeo.
"""

class Eventos:
    """Eventos de Configuración"""
    CONFIG              = "Config    "
    CBIO_CARGA          = "Cbio Carga"
    RECH_CARGA          = "Rech Carga"
    CBIO_DOSIS          = "Cbio Dosis"
    RECH_DOSIS          = "Rech Dosis"
    CBIO_QBOMBA         = "Cbio QBomb"
    RECH_QBOMBA         = "Rech QBomb"
    CBIO_ENCENDIDO      = "Cbio EncBo"
    RECH_ENCENDIDO      = "Rech EncBo"
    CBIO_DESCANSO       = "Cbio DesBo"
    RECH_DESCANSO       = "Rech DesBo"
    CBIO_PORCENTAJE     = "Cbio %Cont"
    RECH_PORCENTAJE     = "Rech %Cont"

    """Eventos de Operación"""
    ESTADO              = "Estado    "
    VB_ABRE             = "VB Abre   "
    VB_CIERRA           = "VB Cierra "
    BOMBA_ARRANCA       = "BombArranc"
    BOMBA_PARA          = "Bomba Para"
    DOSIS_COMPLETADA    = "DosisCompl"
    BOMBA_ATRASADA      = "BombAtrasa"
    BOMBA_RECUPERADA    = "BombaRecup"
    REENCENDIDO         = "Reencendid"
    ENCENDIDO           = "Encendido "
# utils/cdatalog.py
from utils.interfaces import INuevoDia
from utils.ceventos import Eventos
import os

LOG_CONFIG = "log_config.csv"
LOG_OPERATION = "log_operacion.csv"

MAX_LINES_CONFIG = 500
MAX_LINES_OPERATION = 2000
LINE_LENGTH_CONFIG = 90
LINE_LENGTH_OPERATION = 80


class CDatalog(INuevoDia):
    """
    CDatalog según la documentación actualizada.
    - Inicializa correctamente el puntero de escritura aunque se reinicie el dispositivo.
    - Buffer circular real.
    """

    def __init__(self, tiempo, parametros, valvula, bomba, ctdavb, dosificar):
        self.tiempo = tiempo
        self.parametros = parametros
        self.valvula = valvula
        self.bomba = bomba
        self.ctdavb = ctdavb
        self.dosificar = dosificar

        self._create_headers()

        # ←←← CORRECCIÓN IMPORTANTE
        self._current_config = self._calculate_next_line(LOG_CONFIG, MAX_LINES_CONFIG)
        self._current_op = self._calculate_next_line(LOG_OPERATION, MAX_LINES_OPERATION)

        print("\n✅ [CDatalog]")
        print("[CDatalog]   Próxima línea Config:", self._current_config)
        print("[CDatalog]   Próxima línea Operación:", self._current_op)

    def _create_headers(self):
        """Crea encabezados si no existen."""
        try:
            open(LOG_CONFIG, "r").close()
        except OSError:
            line = "Fechora,Fecha,Hora,Evento,Carga,Dosis,QBomba,T Bomba ON,T Bomba OFF,Contraccion"
            if len(line) < LINE_LENGTH_CONFIG:
                line = line + " " * (LINE_LENGTH_CONFIG - len(line) - 1)
            with open(LOG_CONFIG, "w") as f:
                f.write(line + "\n")

        try:
            open(LOG_OPERATION, "r").close()
        except OSError:
            line = "Fechora,Fecha,Hora,Evento,VB,Bomba,TAVB[min],%,Farmaco[ml],%"
            if len(line) < LINE_LENGTH_OPERATION:
                line = line + " " * (LINE_LENGTH_OPERATION - len(line) - 1)
            with open(LOG_OPERATION, "w") as f:
                f.write(line + "\n")

    # ================================================================
    # NUEVA FUNCIÓN: BUSCA EL REGISTRO MÁS NUEVO POR FECHORA Y DEVUELVE LA SIGUIENTE POSICIÓN PARA ESCRIBIR
    # ================================================================
    def _calculate_next_line(self, filename, max_lines):
        """Busca el registro más reciente comparando Fechora 
            Fechora es un string fijo de fecha con el formato yyyymmddhhmmss sin separadores."""
        try:
            with open(filename, "r") as f:
                lines = f.readlines()

            if len(lines) <= 1:          # solo encabezado o archivo vacío
                return 1

            newest_index = 0
            newest_datetime = ""         # string "ddmmyyyyhhmmss"

            for i, line in enumerate(lines[1:], start=1):   # saltamos encabezado
                parts = line.strip().split(',')
                if len(parts) < 1:
                    continue
                current_dt  = parts[0].strip()

                if current_dt > newest_datetime:          # comparación lexicográfica funciona porque el formato es fijo
                    newest_datetime = current_dt
                    newest_index = i

            # La siguiente posición es la que sigue al registro más nuevo (circular)
            next_line = (newest_index % max_lines) + 1
            return next_line

        except OSError:
            # Archivo no existe o error → empezamos desde la primera línea
            return 1
        
    # ================================================================
    # INTERFAZ PÚBLICA
    # ================================================================
    def avisoEventoConfiguracion(self, event_code):
        fechora = self.tiempo.fechora() 
        fecha = self.tiempo.fecha()
        hora = self.tiempo.hora()

        if event_code in [Eventos.CONFIG,Eventos.CBIO_CARGA, Eventos.CBIO_DOSIS, Eventos.CBIO_QBOMBA,
                          Eventos.CBIO_ENCENDIDO, Eventos.CBIO_DESCANSO, Eventos.CBIO_PORCENTAJE]:
            self._log_config(fechora, fecha, hora, event_code)
        elif event_code in [Eventos.RECH_CARGA, Eventos.RECH_DOSIS, Eventos.RECH_QBOMBA,
                            Eventos.RECH_ENCENDIDO, Eventos.RECH_DESCANSO, Eventos.RECH_PORCENTAJE]:
            self._log_rechazo(fechora, fecha, hora, event_code)

    def avisoEventoOperativo(self, event_code):
        fechora = self.tiempo.fechora()
        fecha = self.tiempo.fecha()
        hora = self.tiempo.hora()
        self._log_operation(fechora, fecha, hora, event_code)

    def avisoNuevoDia(self):
        self.avisoEventoConfiguracion(Eventos.CONFIG)
        self.avisoEventoOperativo(Eventos.ESTADO)

    def borrarHistoria(self):
        """Elimina los archivos de log y los recrea con encabezados vacíos."""
        try:
            os.remove(LOG_CONFIG)
        except OSError:
            pass
        try:
            os.remove(LOG_OPERATION)
        except OSError:
            pass
        # Vuelve a crear archivos con encabezados
        self._create_headers()
        # Resetear punteros de escritura
        self._current_config = self._calculate_next_line(LOG_CONFIG, MAX_LINES_CONFIG)
        self._current_op = self._calculate_next_line(LOG_OPERATION, MAX_LINES_OPERATION)
        print("\n[CDatalog] 🗑️  Historia borrada")
        print("[CDatalog]   Próxima línea Config:", self._current_config)
        print("[CDatalog]   Próxima línea Operación:", self._current_op)


    # ================================================================
    # ESCRITURA CIRCULAR
    # ================================================================
    def _log_config(self, fechora, fecha, hora, event_code):
        line = "{},{},{},{},{},{},{},{},{},{}".format(
            fechora, fecha, hora, event_code,
            self.parametros.get_Carga(),
            self.parametros.get_DosisDiariaFarmaco(),
            self.parametros.get_QBomba(),
            self.parametros.get_tiempoMinEncendidoBomba(),
            self.parametros.get_tiempoDescansoBomba(),
            self.parametros.get_porcentajeContraccionTDAVB()
        )
        self._write_fixed(LOG_CONFIG, line, self._current_config, LINE_LENGTH_CONFIG)
        self._current_config = (self._current_config % MAX_LINES_CONFIG) + 1

    def _log_rechazo(self, fechora, fecha, hora, event_code):
        line = "{},{},{},{},,,,,,,".format(fechora, fecha, hora, event_code)
        self._write_fixed(LOG_CONFIG, line, self._current_config, LINE_LENGTH_CONFIG)
        self._current_config = (self._current_config % MAX_LINES_CONFIG) + 1

    def _log_operation(self, fechora, fecha, hora, event_code):         #28
        vb = "A" if self.valvula.valvulaAbierta() else "C"              #29
        bomba = "ON " if self.bomba.esta_encendida() else "OFF"         #32
        tavb_min = self.ctdavb.tiempoAperturaAcumulado() // 60          #36
        tdavb = self.ctdavb.tiempoDiarioApertura()                      #40
        pct_tavb = round(tavb_min * 60 / tdavb * 100, 1) if tdavb > 0 else 0    #45
        farmaco = self.dosificar.remedioAcumulado()                             #52
        target = (self.parametros.get_Carga() / 100.0) * self.parametros.get_DosisDiariaFarmaco()   #57
        pct_farmaco = round(farmaco / target * 100, 1) if target > 0 else 0                         #62
                                                                                                    #+10 "," 72

        line = "{},{},{},{},{},{},{},{},{},{}".format(fechora,
            fecha, hora, event_code, vb, bomba, tavb_min, pct_tavb,
            round(farmaco, 2), pct_farmaco
        )
        self._write_fixed(LOG_OPERATION, line, self._current_op, LINE_LENGTH_OPERATION)
        self._current_op = (self._current_op % MAX_LINES_OPERATION) + 1

    def _write_fixed(self, filename, line, current_line, line_length):
        if len(line) < line_length:
            line = line + " " * (line_length - len(line) - 1)
        elif len(line) > line_length:
            line = line[:line_length - 1]

        try:
            with open(filename, "r+") as f:
                for _ in range(current_line):
                    f.readline()
                f.write(line[:line_length-1] + "\n")
        except OSError:
            pass

    # ================================================================
    # EXPORTACIÓN (estan en orden pueden tener un salto debido a la circularidad)
    # ================================================================
    def exportarLogConfiguracion(self):
        print("Log de Configuración listo")
        return LOG_CONFIG

    def exportarLogOperativo(self):
        print("Log de Operación listo")
        return LOG_OPERATION
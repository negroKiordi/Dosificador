# utils/cdatalog.py
from utils.interfaces import INuevoDia
from utils.ceventos import Eventos

LOG_CONFIG = "log_config.csv"
LOG_OPERATION = "log_operacion.csv"

MAX_LINES_CONFIG = 5# 500
MAX_LINES_OPERATION = 10 # 2000
LINE_LENGTH_CONFIG = 75
LINE_LENGTH_OPERATION = 70


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

        print("✅ CDatalog inicializado correctamente")
        print("   Próxima línea Config:", self._current_config)
        print("   Próxima línea Operación:", self._current_op)

    def _create_headers(self):
        """Crea encabezados si no existen."""
        try:
            open(LOG_CONFIG, "r").close()
        except OSError:
            with open(LOG_CONFIG, "w") as f:
                f.write("Fechora,Fecha,Hora,Evento,Carga,Dosis,QBomba,T Bomba ON,T Bomba OFF,Contraccion")

        try:
            open(LOG_OPERATION, "r").close()
        except OSError:
            with open(LOG_OPERATION, "w") as f:
                f.write("Fechora,Fecha,Hora,Evento,VB,Bomba,TAVB[min],%,Farmaco[ml],%")

    # ================================================================
    # NUEVA FUNCIÓN: BUSCA EL REGISTRO MÁS NUEVO POR FECHA+HORA
    # ================================================================
    def _calculate_next_line(self, filename, max_lines):
        """Busca el registro más reciente comparando Fecha + Hora y devuelve la siguiente posición."""
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

        if event_code in [Eventos.CBIO_CARGA, Eventos.CBIO_DOSIS, Eventos.CBIO_QBOMBA,
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
        self.avisoEventoConfiguracion(Eventos.NUEVO_DIA)
        self.avisoEventoOperativo(Eventos.NUEVO_DIA)

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
            0,
            self.parametros.get_porcentajeContraccionTDAVB()
        )
        self._write_fixed(LOG_CONFIG, line, self._current_config, LINE_LENGTH_CONFIG)
        self._current_config = (self._current_config % MAX_LINES_CONFIG) + 1

    def _log_rechazo(self, fechora, fecha, hora, event_code):
        line = "{},{},{},{},,,,,,,".format(fechora, fecha, hora, event_code)
        self._write_fixed(LOG_CONFIG, line, self._current_config, LINE_LENGTH_CONFIG)
        self._current_config = (self._current_config % MAX_LINES_CONFIG) + 1

    def _log_operation(self, fechora, fecha, hora, event_code):
        vb = "A" if self.valvula.valvulaAbierta() else "C"
        bomba = "ON " if self.bomba.esta_encendida() else "OFF"
        tavb_min = self.ctdavb.tiempoAperturaAcumulado() // 60
        tdavb = self.ctdavb.tiempoDiarioApertura()
        pct_tavb = round(tavb_min * 60 / tdavb * 100, 0) if tdavb > 0 else 0
        farmaco = self.dosificar.remedioAcumulado()
        target = (self.parametros.get_Carga() / 100.0) * self.parametros.get_DosisDiariaFarmaco()
        pct_farmaco = round(farmaco / target * 100, 0) if target > 0 else 0

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
    # EXPORTACIÓN (ordena cronológicamente) 
    # ================================================================
    def exportarLogConfiguracion(self):
        return self._export_circular(LOG_CONFIG, self._current_config, MAX_LINES_CONFIG)

    def exportarLogOperativo(self):
        return self._export_circular(LOG_OPERATION, self._current_op, MAX_LINES_OPERATION)

    def _export_circular(self, filename, current_line, max_lines):
        try:
            with open(filename, "r") as f:
                lines = f.readlines()

            if len(lines) <= 1:
                return filename

            header = lines[0]
            data = lines[1:]

            start = (current_line - 1) % len(data)
            ordered = data[start:] + data[:start]

            with open(filename, "w") as f:
                f.write(header)
                f.writelines(ordered)

            print("Log exportado y ordenado cronológicamente:", filename)
            return filename

        except OSError:
            print("Error al exportar", filename)
            return None
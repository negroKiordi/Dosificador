# utils/cdatalog.py 
from utils.interfaces import INuevoDia  
from utils.ceventos import Eventos

LOG_CONFIG = "log_config.csv"
LOG_OPERATION = "log_operacion.csv"

MAX_LINES_CONFIG = 10 #500
MAX_LINES_OPERATION = 20# 2000

LINE_LENGTH_CONFIG = 61
LINE_LENGTH_OPERATION = 55


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
                f.write("Fecha,Hora,Evento,Carga,Dosis,QBomba,T Bomba ON,T Bomba OFF,Contraccion\n")

        try:
            open(LOG_OPERATION, "r").close()
        except OSError:
            with open(LOG_OPERATION, "w") as f:
                f.write("Fecha,Hora,Evento,VB,Bomba,TAVB[min],%,Farmaco[ml],%\n")

    def _calculate_next_line(self, filename, max_lines):
        """Busca el registro más reciente comparando FECHA + HORA correctamente."""
        try:
            with open(filename, "r") as f:
                lines = f.readlines()

            if len(lines) <= 1:          # solo encabezado o vacío
                return 1

            newest_index = 0
            newest_tuple = (0, 0, 0, 0, 0, 0)   # (año, mes, día, hora, min, seg)

            for i, line in enumerate(lines[1:], start=1):   # saltamos encabezado
                parts = line.strip().split(',')
                if len(parts) < 2:
                    continue

                fecha = parts[0].strip()   # dd-mm-yyyy
                hora  = parts[1].strip()   # hh:mm:ss

                try:
                    d, m, y = map(int, fecha.split('-'))
                    h, mi, s = map(int, hora.split(':'))
                    current_tuple = (y, m, d, h, mi, s)

                    if current_tuple > newest_tuple:
                        newest_tuple = current_tuple
                        newest_index = i
                except:
                    continue   # línea corrupta, la ignoramos

            # Calculamos la siguiente posición (buffer circular)
            next_line = (newest_index % max_lines) + 1
            return next_line

        except OSError:
            return 1   # archivo no existe → empezamos desde el principio       

    # ================================================================
    # INTERFAZ PÚBLICA
    # ================================================================
    def avisoEventoConfiguracion(self, event_code):
        fecha = self.tiempo.fecha()
        hora = self.tiempo.hora()

        if event_code in [Eventos.CBIO_CARGA, Eventos.CBIO_DOSIS, Eventos.CBIO_QBOMBA,
                          Eventos.CBIO_ENCENDIDO, Eventos.CBIO_DESCANSO, Eventos.CBIO_PORCENTAJE]:
            self._log_config(fecha, hora, event_code)
        elif event_code in [Eventos.RECH_CARGA, Eventos.RECH_DOSIS, Eventos.RECH_QBOMBA,
                            Eventos.RECH_ENCENDIDO, Eventos.RECH_DESCANSO, Eventos.RECH_PORCENTAJE]:
            self._log_rechazo(fecha, hora, event_code)

    def avisoEventoOperativo(self, event_code):
        fecha = self.tiempo.fecha()
        hora = self.tiempo.hora()
        self._log_operation(fecha, hora, event_code)

    def avisoNuevoDia(self):
        self.avisoEventoConfiguracion(Eventos.NUEVO_DIA)
        self.avisoEventoOperativo(Eventos.NUEVO_DIA)

    # ================================================================
    # ESCRITURA CIRCULAR
    # ================================================================
    def _log_config(self, fecha, hora, event_code):
        line = "{},{},{},{},{},{},{},{},{}\n".format(
            fecha, hora, event_code,
            self.parametros.get_Carga(),
            self.parametros.get_DosisDiariaFarmaco(),
            self.parametros.get_QBomba(),
            self.parametros.get_tiempoMinEncendidoBomba(),
            0,
            self.parametros.get_porcentajeContraccionTDAVB()
        )
        self._write_fixed(LOG_CONFIG, line, self._current_config, LINE_LENGTH_CONFIG)
        self._current_config = (self._current_config % MAX_LINES_CONFIG) + 1

    def _log_rechazo(self, fecha, hora, event_code):
        line = "{},{},{},,,,,,,,\n".format(fecha, hora, event_code)
        self._write_fixed(LOG_CONFIG, line, self._current_config, LINE_LENGTH_CONFIG)
        self._current_config = (self._current_config % MAX_LINES_CONFIG) + 1

    def _log_operation(self, fecha, hora, event_code):
        vb = "A" if self.valvula.valvulaAbierta() else "C"
        bomba = "ON" if self.bomba.esta_encendida() else "OFF"
        tavb_min = self.ctdavb.tiempoAperturaAcumulado() // 60
        tdavb = self.ctdavb.tiempoDiarioApertura()
        pct_tavb = round(tavb_min * 60 / tdavb * 100, 1) if tdavb > 0 else 0
        farmaco = self.dosificar.remedioAcumulado()
        target = (self.parametros.get_Carga() / 100.0) * self.parametros.get_DosisDiariaFarmaco()
        pct_farmaco = round(farmaco / target * 100, 1) if target > 0 else 0

        line = "{},{},{},{},{},{},{},{},{}\n".format(
            fecha, hora, event_code, vb, bomba, tavb_min, pct_tavb,
            round(farmaco, 2), pct_farmaco
        )
        self._write_fixed(LOG_OPERATION, line, self._current_op, LINE_LENGTH_OPERATION)
        self._current_op = (self._current_op % MAX_LINES_OPERATION) + 1

    def _write_fixed(self, filename, line, current_line, line_length):
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
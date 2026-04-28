# utils/cparametros_operativos.py
import ujson
import config

class CParametrosOperativos:
    """
    Gestiona los parámetros operativos.
    - Carga desde parametros.json
    - Si no existe el archivo → crea uno nuevo con los DEFAULT_PARAMETROS de config.py
    """

    def __init__(self):
        self._valores = config.DEFAULT_PARAMETROS.copy()
        self._load()
        print("CParametrosOperativos cargados desde config.py + parametros.json")

    def _load(self):
        """Carga desde el archivo JSON. Si no existe, lo crea con defaults."""
        try:
            with open(config.ARCHIVO_PARAMETROS, "r") as f:
                datos = ujson.load(f)
                self._valores.update(datos)
            print("Parámetros cargados desde", config.ARCHIVO_PARAMETROS)
        except (OSError, ValueError):
            print("Archivo", config.ARCHIVO_PARAMETROS, "no encontrado o corrupto.")
            print("Creando nuevo archivo con valores por defecto de config.py")
            self._save()

    def _save(self):
        """Guarda los valores actuales en el archivo JSON."""
        try:
            with open(config.ARCHIVO_PARAMETROS, "w") as f:
                ujson.dump(self._valores, f)
        except OSError:
            print("No se pudo guardar parametros.json")

    def _qbomba_alcanza(self, valor_parms):
        '''Computa Qbomba_requerido usando los valores recibidos valor_parms y 
         controla que sea menor a q_bomba.'''
        q_bomba_requerido = self.computa_q_bomba_minimo(valor_parms)
        if q_bomba_requerido > valor_parms["q_bomba"]:
            retorno = { "out": False, \
                    "msj": "Se requiere al menos " + str(q_bomba_requerido) + \
                    " ml/seg." + "Qbomba =" + valor_parms["q_bomba"] + \
                    " Puede ajustar Dosis, tiempo de descanso o Qbedida" +\
                    " antes de aumentar Qbomba."}
        else:
            retorno = {"out": True, \
                       "msj": "Qbomba alcanza. Qbomba requerido =" + \
                              str(q_bomba_requerido) + " ml/seg.", \
                       "q_bomba_minimo": q_bomba_requerido}
        return retorno

    # ================================================================
    # GET / SET
    # ================================================================
    def get_Carga(self):
        return self._valores["carga"]

    def set_Carga(self, carga):
        if carga < 0:
            retorno = {"out": False, "msj": "La carga no puede ser negativa."}
        elif carga > self._valores["carga_maxima_abrevable"]:
            retorno = {"out": False, "msj": "La carga no puede superar " + \
                       str(self._valores["carga_maxima_abrevable"]) + " kg."}
        else:
            self._valores["carga"] = carga
            self._save()
            retorno = {"out": True, "msj": "Carga actualizada a " + str(carga) + " kg."}
        return retorno

    def get_DosisDiariaFarmaco(self):
        return self._valores["dosis_diaria_farmaco"]

    def set_DosisDiariaFarmaco(self, dosis):
        if dosis < 0:
            retorno = {"out": False, "msj": "La dosis no puede ser negativa."}
        else:
            valores_propuestos = self._valores.copy()
            valores_propuestos["dosis_diaria_farmaco"] = dosis
            retorno = self._qbomba_alcanza(valores_propuestos)
            if retorno["out"]:
                # Si la bomba alcanza, se actualiza el valor y q_bomba_minimo
                self._valores["dosis_diaria_farmaco"] = dosis
                self.actualiza_qbombaMinimo(retorno["q_bomba_minimo"])
                self._save()
                retorno["msj"] = "Dosis diaria de fármaco actualizada a " + str(dosis) + " ml/100kg."
        return retorno

    def get_QBomba(self):
        return self._valores["q_bomba"]

    def set_QBomba(self, caudal):
        if caudal <= 0:
            retorno = {"out": False, "msj": "El caudal no puede ser negativo."}
        else:
            valores_propuestos = self._valores.copy()
            valores_propuestos["q_bomba"] = caudal
            retorno = self._qbomba_alcanza(valores_propuestos)
            if retorno["out"]:
                # Si la bomba alcanza, se actualiza el valor y q_bomba_minimo
                self._valores["q_bomba"] = caudal
                self.actualiza_qbombaMinimo(retorno["q_bomba_minimo"])
                self._save()
                retorno["msj"] = "Caudal de la bomba actualizado a " + str(caudal) + " ml/seg."
        return retorno

    def get_porcentajeContraccionTDAVB(self):
        return self._valores["porcentaje_contraccion_tdavb"]

    def set_porcentajeContraccionTDAVB(self, valor):
        if valor < 1 or valor > 99:
            retorno = {"out": False, "msj": "El %taje de Contracción debe estar entre 1 y 99."}
        else:
            self._valores["porcentaje_contraccion_tdavb"] = valor
            self._save()
            retorno = {"out": True, "msj": "%taje de Contracción actualizado a " + str(valor) + " %"}
        return retorno

    def get_tiempoEncendidoBomba(self):
        """Retorna el tiempo de Pulso de encendido de la bomba (segundos)."""
        return self._valores["tiempo_encendido_bomba"]

    def set_tiempoEncendidoBomba(self, valor):
        """Fija el tiempo de encendido (mínimo 1 segundo)."""
        if valor < 1:
            retorno = {"out": False, "msj": "El Tiempo de Encendido debe ser mayor a 0."}
        else:
            valores_propuestos = self._valores.copy()
            valores_propuestos["tiempo_encendido_bomba"] = valor
            retorno = self._qbomba_alcanza(valores_propuestos)
            if retorno["out"]:
                # Si la bomba alcanza, se actualiza el valor y q_bomba_minimo
                self._valores["tiempo_encendido_bomba"] = valor
                self.actualiza_qbombaMinimo(retorno["q_bomba_minimo"])
                self._save()
                retorno["msj"] = "Tiempo Encendido Bomba actualizado a " + str(valor) + " seg."
        return retorno

    def get_tiempoDescansoBomba(self):
        """Retorna el tiempo mínimo de descanso entre dosificaciones (segundos)."""
        return self._valores["tiempo_descanso_bomba"]
    
    def set_tiempoDescansoBomba(self, valor):
        """Fija el tiempo mínimo de descanso (mínimo 0 segundos)."""
        if valor < 0:
            retorno = {"out": False, "msj": "El Tiempo de Descanso no puede ser negativo."}
        else:
            valores_propuestos = self._valores.copy()
            valores_propuestos["tiempo_descanso_bomba"] = valor
            retorno = self._qbomba_alcanza(valores_propuestos)
            if retorno["out"]:
                # Si la bomba alcanza, se actualiza el valor y q_bomba_minimo
                self._valores["tiempo_descanso_bomba"] = valor
                self.actualiza_qbombaMinimo(retorno["q_bomba_minimo"])
                self._save()
                retorno["msj"] = "Tiempo Descanso Bomba actualizado a " + str(valor) + " seg."
        return retorno

    def get_QBebida(self):
        return self._valores["q_bebida"]

    def set_QBebida(self, caudal):
        if caudal <= 0:
            retorno = {"out": False, "msj": "El caudal no puede ser negativo."}
        else:
            valores_propuestos = self._valores.copy()
            valores_propuestos["q_bebida"] = caudal
            retorno = self._qbomba_alcanza(valores_propuestos)
            if retorno["out"]:
                # Si la bomba alcanza, se actualiza el valor y q_bomba_minimo
                self._valores["q_bebida"] = caudal
                self.actualiza_qbombaMinimo(retorno["q_bomba_minimo"])
                self.actualiza_cargaMaximaAbrevable()
                self._save()
                retorno["msj"] = "Caudal de la bebida actualizado a " + str(caudal) + " l/min."
        return retorno

    def get_aguaConsumidaPor100Kg(self):
        return self._valores["agua_consumida_por100Kg"]
 
    def set_aguaConsumidaPor100Kg(self, valor):
        if valor <= 0:
            retorno = {"out": False, "msj": "El valor no puede ser negativo."}
        else:
            valores_propuestos = self._valores.copy() 
            valores_propuestos["agua_consumida_por100Kg"] = valor
            retorno = self._qbomba_alcanza(valores_propuestos)
            if retorno["out"]:
                # Si la bomba alcanza, se actualiza el valor y q_bomba_minimo
                self._valores["agua_consumida_por100Kg"] = valor
                self.actualiza_qbombaMinimo(retorno["q_bomba_minimo"])
                self.actualiza_cargaMaximaAbrevable()
                self._save()
                retorno["msj"] = "Agua consumida/100kg actualizado a " + str(valor) + " l/100kg."
        return retorno

    def get_cargaMaximaAbrevable(self):
            return self._valores["carga_maxima_abrevable"]

    def actualiza_cargaMaximaAbrevable(self):
        """Computa y actualiza sin persisistir el valor de 
           carga_maxima_abrevable usando los parámetros actuales."""
        # carga_max = 1440 [min/día] * q_bebida [lit/min] 
        #              / (agua_consumida_por100Kg [lit/100kg/dia] / 100)
        carga_max = 1440 * \
                    self._valores["q_bebida"] / \
                    self._valores["agua_consumida_por100Kg"] * 100
        self._valores["carga_maxima_abrevable"] = carga_max
        return
    
    def get_qbombaMinimo(self):
        return self._valores["q_bomba_minimo"]  
    
    def actualiza_qbombaMinimo(self, valor):
        '''Si "self._valores["q_bomba_minimo"] != valor" Actualiza sin persistir.'''
        if self._valores["q_bomba_minimo"] != valor:
            self._valores["q_bomba_minimo"] = valor
        return

    def computa_q_bomba_minimo(self, valor_parms):
        """Computa el valor de q_bomba_minimo usando valor_parms."""
        # q_bomba_requerida = q_bebida [lit/min] / 60 [seg/min] 
        #                     * dosis_diaria_farmaco [ml/100kg]
        #                     * ( 1 + tiempo_encendido_bomba / tiempo_descanso_bomba ) 
        #                     / agua_consumida_por100Kg [lit/100kg]
        q_bomba_requerida = (valor_parms["q_bebida"] / 60) * \
                            valor_parms["dosis_diaria_farmaco"]  * \
                            (1 + valor_parms["tiempo_encendido_bomba"] / valor_parms["tiempo_descanso_bomba"]) / \
                            (valor_parms["agua_consumida_por100Kg"] )
        return q_bomba_requerida

    def get_all(self):
        """Devuelve copia de todos los parámetros (útil para web)."""
        return self._valores.copy()

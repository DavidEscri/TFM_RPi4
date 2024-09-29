__author__ = "Jose David Escribano Orts"
__subsystem__ = "Utils"
__module__ = "NEO6Mv2"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

from serial import Serial, SerialException

from tfm_muaii_rpi4.Utils.geolocation.geoUtils import Coordinates
from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton, ContextVarsConst
from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class NmeaMessages:
    GPGGA = "$GPGGA"
    GPGLL = "$GPGLL"
    GPRMC = "$GPRMC"
    GPGSV = "$GPGSV"
    GPGSA = "$GPGSA"


class GPGGASentence:
    POS_UTC_TIME = 1
    POS_LATITUDE = 2
    POS_LATITUDE_INDICATOR = 3
    POS_LONGITUDE = 4
    POS_LONGITUDE_INDICATOR = 5
    POS_FIX_INDICATOR = 6
    POS_SATELLITES_USED = 7
    POS_HORIZONTAL_PRECISION = 8
    POS_MSL_ALTITUDE = 9
    POS_MSL_UNITS = 10
    POS_GEOID_SEPARATION = 11
    POS_GEOID_UNITS = 12


class GPGLLSentence:
    POS_LATITUDE = 1
    POS_LATITUDE_INDICATOR = 2
    POS_LONGITUDE = 3
    POS_LONGITUDE_INDICATOR = 4
    POS_UTC_TIME = 5
    POS_STATUS = 6
    POS_MODE = 7


class GPRMCSentence:
    POS_UTC_TIME = 1
    POS_STATUS = 2
    POS_LATITUDE = 3
    POS_LATITUDE_INDICATOR = 4
    POS_LONGITUDE = 5
    POS_LONGITUDE_INDICATOR = 6
    POS_SPEED_OVER_GROUND = 7
    POS_COURSE_OVER_GROUND = 8
    POS_DATE = 9
    POS_MAGNETIC_VARIATION = 10
    POS_INDICATOR = 11
    POS_MODE = 12


class GPGSVSentence:
    POS_TOTAL_MESSAGES = 1
    POS_NUMBER_MEESAGE = 2
    POS_SATELLITES_IN_VIEW = 3
    POS_SATELLITE_ID_1 = 4
    POS_ELEVATION_1 = 5
    POS_AZIMUTH_1 = 6
    POS_SNR_1 = 7
    POS_SATELLITE_ID_2 = 8
    POS_ELEVATION_2 = 9
    POS_AZIMUTH_2 = 10
    POS_SNR_2 = 11
    POS_SATELLITE_ID_3 = 12
    POS_ELEVATION_3 = 13
    POS_AZIMUTH_3 = 14
    POS_SNR_3 = 15
    POS_SATELLITE_ID_4 = 16
    POS_ELEVATION_4 = 17
    POS_AZIMUTH_4 = 18
    POS_SNR_4 = 19


class GPGSASentence:
    POS_MODE_1 = 1
    POS_MODE_2 = 2
    POS_SATELLITE_USED_1 = 3
    POS_SATELLITE_USED_2 = 4
    POS_SATELLITE_USED_3 = 5
    POS_SATELLITE_USED_4 = 6
    POS_SATELLITE_USED_5 = 7
    POS_SATELLITE_USED_6 = 8
    POS_SATELLITE_USED_7 = 9
    POS_SATELLITE_USED_8 = 10
    POS_SATELLITE_USED_9 = 11
    POS_SATELLITE_USED_10 = 12
    POS_SATELLITE_USED_11 = 13
    POS_SATELLITE_USED_12 = 14
    POS_POSITION_PRECISION = 15
    POS_HORIZONTAL_PRECISION = 16
    POS_VERTICAL_PRECISION = 17


class NEO6Mv2:
    def __init__(self, port: str = "/dev/ttyAMA4", baudrate: int = 9600, timeout: float = 0.5):
        self.__port = port
        self.__baudrate = baudrate
        self.__timeout = timeout
        self.__serial: Serial = None
        self.__current_coordinates: Coordinates = None
        self._context_vars_mgr = ContextVarsMgrSingleton()

    def open(self) -> bool:
        try:
            self.__serial = Serial(self.__port, baudrate=self.__baudrate, timeout=self.__timeout)
            if self.__serial.is_open:
                Logs.get_logger().info(f"Conexión serie GPS establecida en el puerto {self.__port}", extra=__info__)
                return True
            Logs.get_logger().warning(f"No se pudo abrir el puerto {self.__port} para el módulo GPS", extra=__info__)
            return False
        except Exception as e:
            Logs.get_logger().error(f"Error al abrir el puerto {self.__port} para el módulo GPS: {e}", extra=__info__)
            return False

    def close(self):
        try:
            if self.__serial and self.__serial.is_open:
                self.__serial.close()
        except Exception as e:
            Logs.get_logger().error(f"Error al cerrar el puerto serie para el módulo GPS: {e}", extra=__info__)

    def read_sentence(self):
        try:
            sentence = self.__serial.readline().decode("utf-8")
            return self.__process_nmea_sentence(sentence.split(","))
        except SerialException as e:
            Logs.get_logger().error(f"GPS Serial Exception: {e}", extra=__info__)
            return None

    def __process_nmea_sentence(self, nmea_sentence: list) -> bool:
        nmea_message = nmea_sentence[0]
        if len(nmea_message) == 0:
            return False
        nmea_sentence[-1] = nmea_sentence[-1].strip("\r\n")
        res = True
        if nmea_message == NmeaMessages.GPGGA:
            res = self.__process_gpgga_sentence(nmea_sentence)
        elif nmea_message == NmeaMessages.GPGLL:
            res = self.__process_gpgll_sentence(nmea_sentence)
        elif nmea_message == NmeaMessages.GPRMC:
            res = self.__process_gprmc_sentence(nmea_sentence)
        elif nmea_message == NmeaMessages.GPGSV:
            res = self.__process_gpgsv_sentence(nmea_sentence)
        elif nmea_message == NmeaMessages.GPGSA:
            res = self.__process_gpgsa_sentence(nmea_sentence)
        self.__serial.flush()
        return res

    def __process_gpgga_sentence(self, nmea_sentence: list) -> bool:
        fix_indicator = nmea_sentence[GPGGASentence.POS_FIX_INDICATOR]
        valid_fix, fix_type = self.__is_valid_fix(fix_indicator)
        # if len(fix_type) > 0:
        #     Logs.get_logger().debug(f"Modo GPS (GPGGA): {fix_type}", extra=__info__)
        if not valid_fix:
            return False
        latitude = nmea_sentence[GPGGASentence.POS_LATITUDE]
        latitude_indicator = nmea_sentence[GPGGASentence.POS_LATITUDE_INDICATOR]
        longitude = nmea_sentence[GPGGASentence.POS_LONGITUDE]
        longitude_indicator = nmea_sentence[GPGGASentence.POS_LONGITUDE_INDICATOR]
        latitude, longitude = self.__convert_coordinates(latitude, latitude_indicator, longitude, longitude_indicator)
        self.__save_coordinates(latitude, longitude)
        Logs.get_logger().debug(f"Coordenadas GPS (GPGGA): {latitude} {longitude}", extra=__info__)
        satelites_used = nmea_sentence[GPGGASentence.POS_SATELLITES_USED]
        # Logs.get_logger().debug(f"Se están utilizando un total de {satelites_used} satelites", extra=__info__)
        return True

    def __process_gpgll_sentence(self, nmea_sentence: list[str]):
        status = nmea_sentence[GPGLLSentence.POS_STATUS]
        if not self.__is_valid_status(status):
            return False
        mode = nmea_sentence[GPGLLSentence.POS_MODE][:-3]
        valid_mode, mode_type = self.__is_valid_mode(mode)
        # Logs.get_logger().debug(f"Modo GPGLL: {mode_type}", extra=__info__)
        if not valid_mode:
            return False
        latitude = nmea_sentence[GPGLLSentence.POS_LATITUDE]
        latitude_indicator = nmea_sentence[GPGLLSentence.POS_LATITUDE_INDICATOR]
        longitude = nmea_sentence[GPGLLSentence.POS_LONGITUDE]
        longitude_indicator = nmea_sentence[GPGLLSentence.POS_LONGITUDE_INDICATOR]
        latitude, longitude = self.__convert_coordinates(latitude, latitude_indicator, longitude, longitude_indicator)
        self.__save_coordinates(latitude, longitude)
        Logs.get_logger().debug(f"Coordenadas GPS (GPGLL): {latitude} {longitude}", extra=__info__)
        return True

    def __process_gprmc_sentence(self, nmea_sentence: list):
        mode = nmea_sentence[GPRMCSentence.POS_MODE][:-3]
        valid_mode, mode_type = self.__is_valid_mode(mode)
        # Logs.get_logger().debug(f"Modo GPRMC: {mode_type}", extra=__info__)
        if not valid_mode:
            return False
        latitude = nmea_sentence[GPRMCSentence.POS_LATITUDE]
        latitude_indicator = nmea_sentence[GPRMCSentence.POS_LATITUDE_INDICATOR]
        longitude = nmea_sentence[GPRMCSentence.POS_LONGITUDE]
        longitude_indicator = nmea_sentence[GPRMCSentence.POS_LONGITUDE_INDICATOR]
        latitude, longitude = self.__convert_coordinates(latitude, latitude_indicator, longitude, longitude_indicator)
        self.__save_coordinates(latitude, longitude)
        Logs.get_logger().debug(f"Coordenadas GPS (GPRMC): {latitude} {longitude}", extra=__info__)
        return True

    def __process_gpgsv_sentence(self, nmea_sentence: list):
        satelites_totales = nmea_sentence[GPGSVSentence.POS_SATELLITES_IN_VIEW]
        if len(satelites_totales) == 0:
            return False
        self._context_vars_mgr.set_context_var(ContextVarsConst.SATELITES_GNSS, int(satelites_totales))
        Logs.get_logger().debug(f"Se están viendo un total de {satelites_totales} satelites", extra=__info__)
        return True

    def __process_gpgsa_sentence(self, nmea_sentence: list):
        operational_mode = nmea_sentence[GPGSASentence.POS_MODE_2]
        valid_operational_mode, operational_type = self.__is_valid_operational_mode(operational_mode)
        # Logs.get_logger().debug(f"Modo de operacion (GPGSA): {operational_mode}", extra=__info__)
        if not valid_operational_mode:
            return False
        precision_posicion = nmea_sentence[GPGSASentence.POS_POSITION_PRECISION]
        self._context_vars_mgr.set_context_var(ContextVarsConst.PRECISION_GNSS, float(precision_posicion))
        _ = nmea_sentence[GPGSASentence.POS_HORIZONTAL_PRECISION]
        _ = nmea_sentence[GPGSASentence.POS_VERTICAL_PRECISION]
        Logs.get_logger().debug(f"Precision de las coordenadas: {precision_posicion} M", extra=__info__)
        return True

    @staticmethod
    def __is_valid_fix(fix_indicator: str) -> (bool, str):
        if fix_indicator == "0":
            return False, ""
        elif fix_indicator == "1":
            return True, "Modo SPS"
        elif fix_indicator == "2":
            return True, "Modo GPS Diferencial"
        elif fix_indicator == "3":
            return True, "Modo PPS"
        elif fix_indicator == "4":
            return False, "Modo Real Time Kinematic"
        elif fix_indicator == "5":
            return False, "Modo Floating RTK"
        elif fix_indicator == "6":
            return False, "Modo de estimacion"
        elif fix_indicator == "7":
            return False, "Modo de entrada de datos manual"
        elif fix_indicator == "8":
            return False, "Modo simulacion"
        else:
            return False, ""

    @staticmethod
    def __is_valid_status(status: str) -> bool:
        if status == "A":
            return True
        elif status == "V":
            return False
        else:
            return False

    @staticmethod
    def __is_valid_mode(mode: str) -> (bool, str):
        if mode == "N":
            return False, "Datos no validos"
        elif mode == "A":
            return True, "Autonomo"
        elif mode == "D":
            return False, "Diferencial"
        elif mode == "E":
            return False, "Estimado"
        elif mode == "M":
            return False, "Manual"
        elif mode == "S":
            return False, "Simulacion"
        else:
            return False, "No valido"

    @staticmethod
    def __is_valid_operational_mode(operational_mode: str) -> (bool, str):
        if operational_mode == "1":
            return False, "Posicionamiento no disponible"
        elif operational_mode == "2":
            return True, "2D"
        elif operational_mode == "3":
            return True, "3D"
        else:
            return False, "No disponible"

    @staticmethod
    def __convert_coordinates(latitude, latitute_indicator, longitude, longitude_indicator) -> (float, float):
        latitude_degrees = float(latitude[:2])
        latitude_minutes = float(latitude[2:]) / 60
        latitude_decimal = latitude_degrees + latitude_minutes
        if latitute_indicator == "S":
            latitude_decimal *= -1

        longitude_degrees = float(longitude[:2])
        longitude_minutes = float(longitude[2:]) / 60
        longitude_decimal = longitude_degrees + longitude_minutes
        if longitude_indicator == "W":
            longitude_decimal *= -1

        return latitude_decimal, longitude_decimal

    def __save_coordinates(self, latitude: float, longitude: float) -> None:
        self.__current_coordinates = Coordinates(latitude, longitude)
        self._context_vars_mgr.set_context_var(ContextVarsConst.COORDENADAS_GPS, self.__current_coordinates)

    def get_coordinates(self) -> Coordinates:
        return self._context_vars_mgr.get_context_var(ContextVarsConst.COORDENADAS_GPS)

    def get_satellites(self) -> int:
        return self._context_vars_mgr.get_context_var(ContextVarsConst.SATELITES_GNSS)

    def get_precision_gnss(self) -> float:
        return self._context_vars_mgr.get_context_var(ContextVarsConst.PRECISION_GNSS)

__author__ = "Jose David Escribano Orts"
__subsystem__ = "GPSController"
__module__ = "gpsController"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import time

from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.DataPersistence.roadsPersistence import RoadPersistenceSingleton
from tfm_muaii_rpi4.DataPersistence.municipiosPersistence import MunicipiosPersistenceSingleton
from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton, ContextVarsConst, DefaultVarsConst
from tfm_muaii_rpi4.Utils.geolocation.NEO6Mv2 import NEO6Mv2
from tfm_muaii_rpi4.Utils.geolocation.geoUtils import Coordinates, GeoUtils
from tfm_muaii_rpi4.Utils.utils import Service, internet_access

Logs = LogsSingleton()


class _GPSController(Service):
    PORT: str = "/dev/ttyAMA4"
    BAUDRATE: int = 9600
    TIMEOUT: float = 0.5

    def __init__(self):
        super().__init__(__info__, is_thread=True)
        self._context_vars = ContextVarsMgrSingleton()
        self._municipios_pers = MunicipiosPersistenceSingleton()
        self._roads_pers: RoadPersistenceSingleton = None
        self._geo_utils = GeoUtils()
        self.__gps_module: NEO6Mv2 = None
        self.__current_coordinates: Coordinates = None
        self.__last_coordinates: Coordinates = None
        self.__gps_ready: bool = False
        self.sleep_period = 10

    def start(self):
        try:
            while not super().need_stop():
                if not self._start_gps():
                    Logs.get_logger().warning("No se pudo incializar el modulo GPS, próxima intento en 30 segundos",
                                              extra=__info__)
                    time.sleep(30)
                break
            self._municipios_pers.start()
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def _start_gps(self) -> bool:
        try:
            self.__gps_module = NEO6Mv2(self.PORT, self.BAUDRATE, self.TIMEOUT)
            return self.__gps_module.open()
        except Exception as e:
            Logs.get_logger().error(f"Error al iniciar GPS: {e}", extra=__info__)
            return False

    def stop(self):
        try:
            self.__stop_gps()
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def __stop_gps(self) -> bool:
        try:
            self.__gps_module.close()
            return True
        except Exception as e:
            Logs.get_logger().error(f"Error al terminar GPS: {e}", extra=__info__)
            return False

    def _run(self):
        while not super().need_stop() and not self.is_gps_ready():
            super().sleep_period()
            self.__check_gps(sentences_to_read=10)
        while not super().need_stop():
            try:
                if self.is_gps_ready():
                    if not self.__read_gps_sentence():
                        self.__set_gps_ready(False)
                        super().sleep_period()
                        continue
                    if self.__set_initial_coordinates():
                        continue
                    if self.__process_current_coordinates():
                        continue
                    self.__update_vehicle_status()
                    self.__update_location_info()
                else:
                    self.__check_gps(sentences_to_read=5)
                super().sleep_period()
            except Exception as e:
                Logs.get_logger().error(f"Error hilo GPS: {e}", extra=__info__)

    def __check_gps(self, sentences_to_read: int):
        for i in range(sentences_to_read):
            try:
                res = self.__gps_module.read_sentence()
                if res is None:
                    self.__set_default_gps_context_vars()
                    Logs.get_logger().warning("Servicio GPS no disponible, próximo intento en 30 segundos",
                                              extra=__info__)
                    self.sleep_period = 30
                    break
                if not self.is_gps_ready() and res is True:
                    self.__set_gps_ready(True)
                time.sleep(0.1)
            except UnicodeDecodeError:
                Logs.get_logger().error("Sentencia NMEA del módulo GPS incompleta.", extra=__info__)
            except Exception as e:
                self.sleep_period = 10
                Logs.get_logger().error(f"Error al leer sentencia NMEA del GPS: {e}", extra=__info__)

    def __read_gps_sentence(self) -> bool:
        res = self.__gps_module.read_sentence()
        if res is None:
            return False
        return res

    def __set_default_gps_context_vars(self) -> None:
        Logs.get_logger().warning("Cargando valores por defecto para el módulo GPS", extra=__info__)
        self.__set_gps_ready(False)
        self.__current_coordinates = None
        self._context_vars.set_context_var(ContextVarsConst.COORDENADAS_GPS, Coordinates(0, 0))
        self._context_vars.set_context_var(ContextVarsConst.VELOCIDAD_ACTUAL, DefaultVarsConst.CURRENT_SPEED)
        self._context_vars.set_context_var(ContextVarsConst.VELOCIDAD_MAXIMA, DefaultVarsConst.MAX_SPEED)
        self._context_vars.set_context_var(ContextVarsConst.UBICACION_INFO, DefaultVarsConst.LOCATION_INFO)

    def __set_initial_coordinates(self) -> bool:
        if self.__current_coordinates is None:
            self.__current_coordinates = self.get_coordinates()
            return True
        self.__last_coordinates = self.__current_coordinates
        return False

    def __process_current_coordinates(self) -> bool:
        """
        Método encargado de procesar las coordenadas actuales y las anteriores. En caso de no que no sean válidas, se
        deberán volver a procesar.
        :return bool: Coordenadas no validas (True) - Coordenadas validas (False)
        """
        if not self.__last_coordinates.valid_coordinates():
            self.__set_default_gps_context_vars()
            return True
        self.__current_coordinates = self.get_coordinates()
        if not self.__current_coordinates.valid_coordinates():
            self.__set_default_gps_context_vars()
            return True
        return False

    def __update_vehicle_status(self) -> None:
        current_speed = self._geo_utils.calculate_speed(self.__last_coordinates, self.__current_coordinates)
        Logs.get_logger().info(f"Velocidad actual: {current_speed} km/h", extra=__info__)
        self._context_vars.set_context_var(ContextVarsConst.VELOCIDAD_ACTUAL, current_speed)
        # TODO: Cambiar a: current_speed < 2 o current_speed < 5?
        self._context_vars.set_context_var(ContextVarsConst.VEHICULO_PARADO, current_speed == 0)

    def __update_location_info(self) -> None:
        max_speed, location_info = self.__get_speed_and_location_info()
        self._context_vars.set_context_var(ContextVarsConst.VELOCIDAD_MAXIMA, max_speed)
        self._context_vars.set_context_var(ContextVarsConst.UBICACION_INFO, location_info)

    def __get_speed_and_location_info(self) -> (int, str):
        if internet_access():
            max_speed, location_info = self._geo_utils.get_online_max_speed_and_location(self.__current_coordinates)
            self.__update_online_road_persistence(location_info)
            return max_speed, location_info
        else:
            Logs.get_logger().warning("No hay conexión a internet para realizar la geolocalización", extra=__info__)
            current_municipio = self._municipios_pers.get_current_municipio()
            record_municipio = self._municipios_pers.get_record_municipio(self.__current_coordinates)
            provincia = self._municipios_pers.get_current_provincia()
            if self._roads_pers is None or record_municipio["municipio"] != current_municipio:
                road_db_name = self._geo_utils.convert_provincia_to_road_db(provincia)
                self._roads_pers = RoadPersistenceSingleton(road_db_name)
                self._roads_pers.start()
            current_road = self._roads_pers.get_record_by_coordinates(self.__current_coordinates.get_coordinates()[::-1])
            self.__current_road_name = current_road["nombre"]
            current_road.update({"provincia": provincia})
            current_road.update({"municipio": record_municipio["municipio"]})
            self.__update_offline_road_persistence(current_road)
            return self._geo_utils.get_offline_max_speed_and_location(current_road)

    def __update_online_road_persistence(self, road_info: str):
        pass

    def __update_offline_road_persistence(self, road_info: dict):
        pass

    def __set_gps_ready(self, value: bool):
        self.__gps_ready = value

    def is_gps_ready(self) -> bool:
        return self.__gps_ready

    def get_coordinates(self) -> Coordinates:
        return self.__gps_module.get_coordinates()


class GPSControllerSingleton:
    __instance = None

    def __new__(cls):
        if GPSControllerSingleton.__instance is None:
            GPSControllerSingleton.__instance = _GPSController()
        return GPSControllerSingleton.__instance

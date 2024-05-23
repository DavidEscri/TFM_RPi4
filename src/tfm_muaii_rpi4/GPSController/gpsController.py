__author__ = "Jose David Escribano Orts"
__subsystem__ = "GPSController"
__module__ = "gpsController"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import time

from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton, ContextVarsConst
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
        self._geo_utils = GeoUtils()
        self._gps_module: NEO6Mv2 = None
        self.current_coordinates: Coordinates = None
        self.last_coordinates: Coordinates = None
        self.sleep_period = 1

    def start(self):
        try:
            self._start_gps()
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def _start_gps(self) -> bool:
        try:
            self._gps_module = NEO6Mv2(self.PORT, self.BAUDRATE, self.TIMEOUT)
            return self._gps_module.open()
        except Exception as e:
            Logs.get_logger().error(f"Error al iniciar GPS: {e}", extra=__info__)
            return False

    def stop(self):
        self._stop_gps()
        super().stop()

    def _stop_gps(self) -> bool:
        try:
            self._gps_module.close()
            return True
        except Exception as e:
            Logs.get_logger().error(f"Error al terminar GPS: {e}", extra=__info__)
            return False

    def _run(self):
        try:
            while not super().need_stop():
                if not self._read_gps_sentence():
                    super().sleep_period()
                    continue
                if self._set_initial_coordinates():
                    continue
                if self._process_current_coordinates():
                    continue
                self._update_vehicle_status()
                self._update_location_info()
                super().sleep_period()
        except Exception as e:
            Logs.get_logger().error(f"Error hilo GPS: {e}", extra=__info__)

    def _read_gps_sentence(self) -> bool:
        if not self._gps_module.read_sentence():
            self._set_default_context_vars()
            Logs.get_logger().warning("Servicio GPS no disponible, próximo intento en 10 segundos",
                                      extra=__info__)
            self.sleep_period = 10
            return False
        self.sleep_period = 1
        return True

    def _set_default_context_vars(self) -> None:
        self.current_coordinates = None
        self._context_vars.set_context_var(ContextVarsConst.COORDENADAS_GPS, Coordinates(0, 0))
        self._context_vars.set_context_var(ContextVarsConst.VELOCIDAD_ACTUAL, None)
        self._context_vars.set_context_var(ContextVarsConst.VELOCIDAD_MAXIMA, None)
        self._context_vars.set_context_var(ContextVarsConst.UBICACION_INFO, "")

    def _set_initial_coordinates(self) -> bool:
        if self.current_coordinates is None:
            self.current_coordinates = self.get_coordinates()
            return True
        self.last_coordinates = self.current_coordinates
        return False

    def _process_current_coordinates(self) -> bool:
        if self.last_coordinates.check_coordinates():
            return True
        self.current_coordinates = self.get_coordinates()
        if self.current_coordinates.check_coordinates():
            return True
        return False

    def get_coordinates(self) -> Coordinates:
        return self._gps_module.get_coordinates()

    def _update_vehicle_status(self) -> None:
        current_speed = self._geo_utils.calculate_speed(self.last_coordinates, self.current_coordinates)
        Logs.get_logger().info(f"Velocidad actual: {current_speed} km/h", extra=__info__)
        self._context_vars.set_context_var(ContextVarsConst.VELOCIDAD_ACTUAL, current_speed)
        self._context_vars.set_context_var(ContextVarsConst.VEHICULO_PARADO, current_speed == 0)

    def _update_location_info(self) -> None:
        max_speed, location_info = self._get_speed_and_location_info()
        self._context_vars.set_context_var(ContextVarsConst.VELOCIDAD_MAXIMA, max_speed)
        self._context_vars.set_context_var(ContextVarsConst.UBICACION_INFO, location_info)

    def _get_speed_and_location_info(self) -> (int, str):
        if internet_access():
            return self._geo_utils.get_max_speed_location(self.current_coordinates)
        else:
            Logs.get_logger().warning("No hay conexión a internet para realizar la geolocalización", extra=__info__)
            return self._geo_utils.get_offline_max_speed_location(self.current_coordinates)


class GPSControllerSingleton:
    __instance = None

    def __new__(cls):
        if GPSControllerSingleton.__instance is None:
            GPSControllerSingleton.__instance = _GPSController()
        return GPSControllerSingleton.__instance

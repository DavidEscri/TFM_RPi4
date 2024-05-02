__author__ = "Jose David Escribano Orts"
__subsystem__ = "GPSController"
__module__ = "gpsController"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import serial
import time

from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.geolocation.NEO6Mv2 import NEO6Mv2
from tfm_muaii_rpi4.Utils.geolocation.geoUtils import Coordinates, GeoUtils
from tfm_muaii_rpi4.Utils.display.displayOLED import OLEDController
from tfm_muaii_rpi4.Utils.utils import Service

Logs = LogsSingleton()


class _GPSController(Service):
    PORT: str = "/dev/ttyAMA4"
    BAUDRATE: int = 9600
    TIMEOUT: float = 0.5

    def __init__(self):
        super().__init__(__info__, is_thread=True)
        self._gps_module: NEO6Mv2 = None
        self._geo_utils = GeoUtils()
        self._oled_mgr = OLEDController()
        self.current_coordinates: Coordinates = None
        self.last_coordinates: Coordinates = None

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
                res = self._gps_module.read_sentence()
                if not res:
                    Logs.get_logger().warning("Servicio GPS no disponible", extra=__info__)
                    self._oled_mgr.draw_speed_limit(None, None, "")
                    time.sleep(30)
                    continue
                if self.current_coordinates is None:
                    self.current_coordinates = self.get_coordinates()
                    continue
                else:
                    self.last_coordinates = self.current_coordinates
                self.current_coordinates = self.get_coordinates()
                current_speed = self._geo_utils.calculate_speed(self.last_coordinates, self.current_coordinates)
                max_speed, location_info = self._geo_utils.get_max_speed_location(self.current_coordinates)
                Logs.get_logger().info(f"Velocidad actual: {current_speed} km/h", extra=__info__)
                self._oled_mgr.draw_speed_limit(max_speed, current_speed, location_info)
                time.sleep(1)
        except Exception as e:
            Logs.get_logger().error(f"Error GPS: {e}", extra=__info__)

    def get_coordinates(self) -> Coordinates:
        return self._gps_module.get_coordinates()


class GPSControllerSingleton:
    __instance = None

    def __new__(cls):
        if GPSControllerSingleton.__instance is None:
            GPSControllerSingleton.__instance = _GPSController()
        return GPSControllerSingleton.__instance

if __name__ == "__main__":
    gps_module = GPSControllerSingleton()
    gps_module.start()

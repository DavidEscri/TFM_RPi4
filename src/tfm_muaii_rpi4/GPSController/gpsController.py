__author__ = "David Escribano"
__subsystem__ = "GPSController"
__module__ = "gpsController"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import serial
import time

from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.geolocation.NEO6Mv2 import NEO6Mv2
from tfm_muaii_rpi4.Utils.geolocation.geoUtils import Coordinates, GeoUtils
from tfm_muaii_rpi4.Utils.utils import Service

Logs = LogsSingleton()


class GPSController(Service):
    PORT: str = "/dev/ttyAMA4"
    BAUDRATE: int = 9600
    TIMEOUT: float = 0.5

    def __init__(self):
        super().__init__(__info__, True)
        self.gps_module: NEO6Mv2 = None

    def start(self):
        try:
            self.start_gps()
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def start_gps(self) -> bool:
        try:
            self.gps_module = NEO6Mv2(self.PORT, self.BAUDRATE, self.TIMEOUT)
            return self.gps_module.open()
        except Exception as e:
            Logs.get_logger().error(f"Error al iniciar GPS: {e}", extra=__info__)
            return False

    def stop(self):
        self.stop_gps()
        super().stop()

    def stop_gps(self) -> bool:
        try:
            self.gps_module.close()
            return True
        except Exception as e:
            Logs.get_logger().error(f"Error al terminar GPS: {e}", extra=__info__)
            return False

    def _run(self):
        try:
            self.gps_module.read_sentence()
            time.sleep(1)
        except Exception as e:
            Logs.get_logger().error(f"Error GPS: {e}", extra=__info__)

    def get_coordinates(self):
        latitude = self.gps_module.get_latitude()
        longitude = self.gps_module.get_longitude()
        return Coordinates(latitude, longitude)


class GPSControllerAgentSingleton:
    __instance = None

    def __new__(cls):
        if GPSControllerAgentSingleton.__instance is None:
            GPSControllerAgentSingleton.__instance = GPSController()
        return GPSControllerAgentSingleton.__instance

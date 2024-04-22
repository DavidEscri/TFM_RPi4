__author__ = "Jose David Escribano Orts"
__subsystem__ = "Main"
__module__ = "startUpMgr"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os
import time
from datetime import datetime

from tfm_muaii_rpi4.DataPersistence.dataPersistenceMgr import DataPersistenceMgrSingleton
from tfm_muaii_rpi4.PeopleDetector.peopleCounter import PeopleCounterSingleton
from tfm_muaii_rpi4.GPSController.gpsController import GPSControllerSingleton
from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class _StartUpDownMgr:
    SYS_SHUTDOWN: int = 2
    SYS_RESTART: int = 1
    NOT_EXIT: int = 0

    def __init__(self):
        try:
            Logs.get_logger().info(f"Inicio Aplicación {datetime.now()}....", extra=__info__)
            self.env = EnvSingleton()
            self.data_persistence = DataPersistenceMgrSingleton()
            self.people_counter = PeopleCounterSingleton()
            self.gps_controller = GPSControllerSingleton()
            self.exit_flag = self.NOT_EXIT
        except Exception as e:
            self._critical_error(e, "init")

    def start(self):
        """
        """
        counter: int = 0
        Logs.get_logger().info("Inicio de los servicios en entorno %s", self.env.get_env(), extra=__info__)
        self._start_services()
        while self.exit_flag == self.NOT_EXIT:
            time.sleep(5)
            counter += 5
            if counter % 1800 == 0:
                date = datetime.now()
                if date.hour == 3 and counter > 3600:
                    # Reinicio si la RPi4 lleva encendido más de 1 hora encendida y son las 3 de la mañana.
                    self.exit_flag = self.SYS_RESTART
        self.exit_app(self.exit_flag)

    def stop(self):
        """
        """
        time_1 = time.time()
        self._stop_services()
        time_2 = time.time()
        time_interval = time_2 - time_1
        Logs.get_logger().info("Parada del sistema en %s segundos", round(time_interval, 2), extra=__info__)

    def _start_services(self):
        self.data_persistence.start()
        self.people_counter.start()
        self.gps_controller.start()

    def _stop_services(self):
        self.people_counter.stop()
        self.data_persistence.stop()
        self.gps_controller.stop()

    def exit_app(self, exit_control: int):
        self.stop()
        if exit_control is self.SYS_SHUTDOWN:
            os.system("(sleep 5; sudo shutdown now) & ")
        else:
            os.system("(sleep 5; sudo reboot) & ")
        exit(exit_control)

    def _critical_error(self, err, funct: str) -> None:
        Logs.get_logger().critical(f"Error critico en función {funct} en el servicio: {err}", exc_info=True,
                                   extra=__info__)


class StartUpMgrSingleton:
    # storage for the instance reference
    __instance = None

    def __new__(cls):
        if StartUpMgrSingleton.__instance is None:
            StartUpMgrSingleton.__instance = _StartUpDownMgr()
        return StartUpMgrSingleton.__instance

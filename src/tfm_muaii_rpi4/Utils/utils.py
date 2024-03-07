__author__ = "Jose David Escribano Orts"
__subsystem__ = "Utils"
__module__ = "utils"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import datetime
import time

from threading import Thread, Event
from abc import abstractmethod

from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class Service:
    EST_INICIANDO = 1
    EST_EJECUTANDO = 2
    EST_PARADO = 3
    EST_ERR = 4

    def __init__(self, info: dict, is_thread: bool = False):
        self._status = Service.EST_INICIANDO
        self._info = info
        self._is_thread = is_thread
        self._stop_thread = None
        self._thread_srv: Thread = None
        self.sleep_period = 0
        if self._is_thread:
            self.sleep_period = 1
            self._stop_thread = Event()
        self._start_time = datetime.datetime.now()

    @property
    def get_status(self):
        return self._status

    @staticmethod
    def _get_status_name(status: int) -> str:
        names = ["Iniciando", "Ejecutando", "Parado", "Error"]
        return names[status - 1]

    def start(self):
        if self._is_thread:
            if not self._get_run_status():
                self._stop_thread.clear()
                self._thread_srv = Thread(target=self._run)
                self._thread_srv.daemon = True
                self._thread_srv.name = f"THREAD_{self._info['module_name']}"
                Logs.get_logger().debug("Levantando en servicio %s hilo %s", self._info["module_name"],
                                        self._thread_srv.name, extra=self._info)
                self._thread_srv.start()
                self._status = Service.EST_EJECUTANDO
        else:
            self._status = Service.EST_EJECUTANDO

    def _run(self):
        pass

    def sleep_period(self):
        count: int = 0
        while not (self.need_stop() or count > self.sleep_period):
            time.sleep(1)
            count = count + 1

    def stop(self):
        if self._is_thread:
            self._stop_thread.set()
            self._thread_srv.join(self.sleep_period + 1)
            if self._thread_srv.is_alive():
                Logs.get_logger().warn("No fue posible la salida de servicio %s hilo %s", self._info["module_name"],
                                       self._thread_srv.name, extra=self._info)
            else:
                Logs.get_logger().info("Salida de servicio %s hilo %s", self._info["module_name"],
                                       self._thread_srv.name, extra=self._info)
        else:
            Logs.get_logger().info("Salida de servicio %s", self._info["module_name"], extra=self._info)

    def _get_run_status(self):
        """
        Devuelve True si el módulo se está ejecutando
        """
        if self._thread_srv is not None:
            return self._thread_srv.is_alive()
        else:
            return False

    def need_stop(self) -> bool:
        return self._stop_thread.is_set()

    def critical_error(self, err, funct: str) -> None:
        """
        Reporta un error crítico al servicio
        :return:
        """
        Logs.get_logger().critical("Error critico en función %s en el servicio : %s", funct, err,
                                   exc_info=True, extra=self._info)
        self._status = Service.EST_ERR

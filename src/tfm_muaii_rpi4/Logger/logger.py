__author__ = "Jose David Escribano Orts"
__subsystem__ = "Logger"
__module__ = "logs"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import logging
import os
import time
from datetime import datetime

from tfm_muaii_rpi4.Environment import env


class _Logs:
    NOTSET = logging.NOTSET
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    LOGGER_NAME = "logger_TFM_RPi4"
    FORMATO = "%(asctime)s %(levelname)s %(subsystem)-15s %(module_name)-8s %(version)-3s %(message)s"

    def __init__(self):
        # Se crea el logger
        self.__logger = logging.getLogger(_Logs.LOGGER_NAME)
        # Se crea el handler y se le asigna una fecha de registro
        date = datetime.now().strftime('%Y%m%d')
        setting = env.EnvSingleton()
        self.path_logs = setting.get_path(setting.logs_path)
        if not os.path.exists(self.path_logs):
            os.makedirs(self.path_logs)
        file_name = 'tfm_{}.log'.format(date)
        file_name = os.path.join(self.path_logs, file_name)
        self.handler_file = logging.FileHandler(file_name)
        # Se añade el handler al logger creado
        self.__logger.addHandler(self.handler_file)
        # Se establece un nivel de logeo
        self.__logger.setLevel(self.DEBUG)
        # Se define un formato de escritura del log
        self.handler_file.setFormatter(logging.Formatter(_Logs.FORMATO))
        self._clean_logs(self.path_logs)

    def get_logger(self):
        return self.__logger

    def _clean_logs(self, path_logs: str):
        try:
            pass
        except Exception as e:
            self.__logger.error(f"Error en el empaquetado de logs: {e}", extra=__info__)


class LogsSingleton:
    __instance = None

    def __new__(cls):
        if LogsSingleton.__instance is None:
            LogsSingleton.__instance = _Logs()
        return LogsSingleton.__instance

__author__ = "Jose David Escribano Orts"
__subsystem__ = "Logger"
__module__ = "logs"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import logging
import os
import tarfile
from datetime import datetime, timedelta

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
        # Configuración del path y archivo de log
        setting = env.EnvSingleton()
        self.path_logs = setting.get_path(setting.logs_path)
        if not os.path.exists(self.path_logs):
            os.makedirs(self.path_logs)
        # Se crea un handler y se asigna al logger
        self._setup_file_handler()
        # Se establece un nivel de logeo
        self.__logger.setLevel(self.DEBUG)
        # Se define un formato de escritura del log
        self.handler_file.setFormatter(logging.Formatter(_Logs.FORMATO))
        # Limpieza logs antiguos
        self._clean_logs(self.path_logs)

    def _setup_file_handler(self):
        date = datetime.now().strftime('%Y%m%d')
        file_name = 'tfm_{}.log'.format(date)
        file_name = os.path.join(self.path_logs, file_name)
        # Inicializar el FileHandler
        self.handler_file = logging.FileHandler(file_name)
        # Se añade el handler al logger creado
        if not self.__logger.hasHandlers():
            self.__logger.addHandler(self.handler_file)

    def get_logger(self):
        return self.__logger

    def _clean_logs(self, path_dir: str):
        try:
            yesterday = datetime.now() - timedelta(days=1)
            for log_file in os.listdir(path_dir):
                log_path = os.path.join(path_dir, log_file)
                if os.path.isdir(log_path) or not log_file.endswith(".log"):
                    continue
                output_log_name = log_file[:log_file.find(".")] + ".tgz"
                output_log_path = os.path.join(path_dir, output_log_name)
                file_log_stat = os.stat(log_path)
                file_log_date = datetime.fromtimestamp(file_log_stat.st_mtime)
                if file_log_date < yesterday:
                    with tarfile.open(output_log_path, "w:gz") as tar:
                        tar.add(log_path)
                    os.remove(log_path)

        except Exception as e:
            self.__logger.error(f"Error en el empaquetado de logs: {e}", extra=__info__)

class LogsSingleton:
    __instance = None

    def __new__(cls):
        if LogsSingleton.__instance is None:
            LogsSingleton.__instance = _Logs()
        return LogsSingleton.__instance

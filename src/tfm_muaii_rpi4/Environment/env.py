__author__ = "Jose David Escribano Orts"
__subsystem__ = "Environment"
__module__ = "env"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import json
import logging
import os


class _Env:
    """
    Gestiona la configuración en el entorno de ejecución de la aplicación
    """
    TEST = "test"
    RPi4 = "RPi4"
    DEFAULT = "test"
    PATHS = "paths"
    HOSTS = "hosts"

    # variables
    images_test_path = "images_test_path"
    images_result_path = "images_result_path"
    logs_path = "logs_path"
    yolo_classes_path = "yolo_classes_path"
    yolo_models_path = "yolo_models_path"

    raspberry = "raspberry"
    IP = "IP"

    def __init__(self):
        env: str = os.getenv("APP_ENVIRONMENT")
        if env is None:
            self._env = _Env.TEST
            logging.error("No existe el environment asignado", extra=__info__)
        else:
            self._env = env
        self.app_path: str = os.getenv("APP_SETTINGS_PATH")
        if self.app_path is None:
            self.app_path = "D:\\PyCharm Community Edition\\Proyectos\\TFM_MUAII"
        self.setting_path = os.path.join(self.app_path, 'settings.json')
        with open(self.setting_path, 'r') as f:
            setting_dict = json.load(f)
        self._conf: dict = setting_dict

    def get_env(self) -> str:
        return self._env

    def get_path(self, path: str) -> str:
        if path in self._conf[self.PATHS]:
            if self._env in self._conf[self.PATHS][path]:
                return self._conf[self.PATHS][path][self._env]
            else:
                return self._conf[self.PATHS][path][self.DEFAULT]
        else:
            logging.error(f"No existe el path {path}", extra=__info__)
            return None

    def get_host(self, service: str) -> dict:
        if self._conf is not None:
            if service in self._conf[self.HOSTS]:
                return self._conf[self.HOSTS][service]
        else:
            logging.error(f"No existe el host {service}", extra=__info__)
            return None

    def get_app_path(self) -> str:
        return self.app_path

    def get_setting_path(self) -> str:
        return self.setting_path


class EnvSingleton:
    __instance = None

    def __new__(cls):
        if EnvSingleton.__instance is None:
            EnvSingleton.__instance = _Env()
        return EnvSingleton.__instance
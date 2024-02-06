__author__ = "Jose David Escribano Orts"
__subsystem__ = "Main"
__module__ = "startUpMgr"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import logging
import os
import threading
import time
from datetime import datetime

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class _startUpDownMgr:
    """
    Implementa el servicio de arranque de la aplicación.
    """

    def __init__(self, callback_plugin: callable = None):
        try:
            Logs.get_logger().info(f"Inicio Aplicación {datetime.now()}....", extra=__info__)
            self.env = EnvSingleton()
            self.callback_plugin = callback_plugin

        except Exception as e:
            self._critical_error(e, "init")

    def start(self):
        """
        """
        pass

    def stop(self):
        """
        """
        pass

    def _critical_error(self, err, funct: str) -> None:
        Logs.get_logger().critical(f"Error critico en función {funct} en el servicio: {err}", exc_info=True,
                                   extra=__info__)


class startUpMgrSingleton:
    # storage for the instance reference
    __instance = None

    def __new__(cls, callback_plugin: callable = None):
        if startUpMgrSingleton.__instance is None:
            startUpMgrSingleton.__instance = startUpMgrSingleton(callback_plugin)
        return startUpMgrSingleton.__instance
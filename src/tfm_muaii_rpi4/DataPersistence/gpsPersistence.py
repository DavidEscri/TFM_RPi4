__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "gpsPersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service


Logs = LogsSingleton()


class _GPSPersistence(Service):
    def __init__(self):
        super().__init__(__info__, is_thread=False)
        pass

    def start(self):
        try:
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")


class GpsPersistenceSingleton:
    __instance = None

    def __new__(cls):
        if GpsPersistenceSingleton.__instance is None:
            GpsPersistenceSingleton.__instance = _GPSPersistence()
        return GpsPersistenceSingleton.__instance
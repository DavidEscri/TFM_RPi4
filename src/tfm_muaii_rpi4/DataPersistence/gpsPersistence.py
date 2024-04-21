__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "gpsPersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class _GPSPersistence:
    def __init__(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class GpsPersistenceSingleton:
    __instance = None

    def __new__(cls):
        if GpsPersistenceSingleton.__instance is None:
            GpsPersistenceSingleton.__instance = _GPSPersistence()
        return GpsPersistenceSingleton.__instance
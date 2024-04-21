__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "peoplePersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class _PeoplePersistence:
    def __init__(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class PeoplePersistenceSingleton:
    __instance = None

    def __new__(cls):
        if PeoplePersistenceSingleton.__instance is None:
            PeoplePersistenceSingleton.__instance = _PeoplePersistence()
        return PeoplePersistenceSingleton.__instance
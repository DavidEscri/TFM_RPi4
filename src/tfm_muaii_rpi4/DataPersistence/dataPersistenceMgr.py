__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "dataPersistenceMgr"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton
from tfm_muaii_rpi4.DataPersistence.peoplePersistence import PeoplePersistenceSingleton
from tfm_muaii_rpi4.DataPersistence.gpsPersistence import GpsPersistenceSingleton


class _DataPersistence():
    def __init__(self):
        self.context_vars_mgr = ContextVarsMgrSingleton()
        self.people_persistence = PeoplePersistenceSingleton()
        self.gps_persistence = GpsPersistenceSingleton()

    def start(self):
        self.context_vars_mgr.start()
        self.people_persistence.star()
        self.gps_persistence.start()

    def stop(self):
        self.context_vars_mgr.stop()
        self.people_persistence.stop()
        self.gps_persistence.stop()


class DataPersistenceMgrSingleton:
    __instance = None

    def __new__(cls):
        if DataPersistenceMgrSingleton.__instance is None:
            DataPersistenceMgrSingleton.__instance = _DataPersistence()
        return DataPersistenceMgrSingleton.__instance
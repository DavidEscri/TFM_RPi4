__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "gpsPersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os
from datetime import datetime

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service, ServiceDB


Logs = LogsSingleton()


class _GPSPersistence(Service, ServiceDB):
    DB_NAME = "DB_gps.db"
    _table_name: str = "GPS"
    _list_fields: list = ["id", "coordenadas", "date_create", "date_update"]
    _list_fields_type: list = ["INTEGER", "JSON", "TIMESTAMP", "TIMESTAMP"]
    _primary_key: str = "id AUTOINCREMENT"

    POS_ID: int = 0
    POS_COORDENADAS: int = 1
    POS_DATE_CREATE: int = 2
    POS_DATE_UPDATE: int = 3

    def __init__(self):
        Service.__init__(self, __info__, is_thread=False)
        try:
            env = EnvSingleton()
            db_path = env.get_path(env.DB_path)
            ServiceDB.__init__(self, self.DB_NAME, db_path)
        except Exception as e:
            super().critical_error(e, "init")

    def start(self):
        try:
            super().start()
            if not os.path.isfile(self.path_db):
                if not self._create_db_gps():
                    raise Exception(f"Error al crear la base de datos {self.path_db}")
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def insert_coordenadas(self, record: dict) -> bool:
        now = datetime.now()
        record[self._list_fields[self.POS_DATE_CREATE]] = now
        return self.insert_record_db(self._table_name, self._list_fields, record)

    def _create_db_gps(self) -> bool:
        """
        Se encarga de crear db de sessions.
        """
        Logs.get_logger().info("Creando base de datos %s", self.path_db, extra=__info__)
        return self.create_table(self._table_name, self._list_fields, self._list_fields_type, self._primary_key)


class GpsPersistenceSingleton:
    __instance = None

    def __new__(cls):
        if GpsPersistenceSingleton.__instance is None:
            GpsPersistenceSingleton.__instance = _GPSPersistence()
        return GpsPersistenceSingleton.__instance
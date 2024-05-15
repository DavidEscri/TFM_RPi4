__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "peoplePersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os
from datetime import datetime

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service, ServiceDB


Logs = LogsSingleton()


class _PeoplePersistence(Service, ServiceDB):
    DB_NAME = "DB_people.db"
    _table_name: str = "PEOPLE"
    _list_fields: list = ["id", "personas_actuales", "municipio", "provincia", "date_create", "date_update"]
    _list_fields_type: list = ["INTEGER", "INTEGER", "VARCHAR(20)", "VARCHAR(20)", "TIMESTAMP", "TIMESTAMP"]
    _primary_key: str = "id AUTOINCREMENT"

    POS_ID: int = 0
    POS_PERSONAS: int = 1
    POS_MUNICIPIO: int = 2
    POS_PROVINCIA: int = 3
    POS_DATE_CREATE: int = 4
    POS_DATE_UPDATE: int = 5

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
                if not self._create_db_people():
                    raise Exception(f"Error al crear la base de datos {self.path_db}")
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def insert_current_people(self, record: dict) -> bool:
        now = datetime.now()
        record[self._list_fields[self.POS_DATE_CREATE]] = now
        return self.insert_record_db(self._table_name, self._list_fields, record)

    def get_record_by_municipio(self, municipio: str) -> (bool, list):
        fields: list = list()
        params: list = list()
        for i in range(0, len(self._list_fields)):
            fields.append(self._list_fields[i])
        params.append(municipio)
        sql: str = f"SELECT {', '.join(fields)} FROM {self._table_name} WHERE {fields[self.POS_MUNICIPIO]} = ?"
        return self._db.query_sql(sql, tuple(params), self._list_fields)

    def get_record_by_pronvincia(self, provincia: str):
        fields: list = list()
        params: list = list()
        for i in range(0, len(self._list_fields)):
            fields.append(self._list_fields[i])
        params.append(provincia)
        sql: str = f"SELECT {', '.join(fields)} FROM {self._table_name} WHERE {fields[self.POS_PROVINCIA]} = ?"
        return self._db.query_sql(sql, tuple(params), self._list_fields)

    def _create_db_people(self) -> bool:
        """
        Se encarga de crear db de sessions.
        """
        Logs.get_logger().info("Creando base de datos %s", self.path_db, extra=__info__)
        return self.create_table(self._table_name, self._list_fields, self._list_fields_type, self._primary_key)


class PeoplePersistenceSingleton:
    __instance = None

    def __new__(cls):
        if PeoplePersistenceSingleton.__instance is None:
            PeoplePersistenceSingleton.__instance = _PeoplePersistence()
        return PeoplePersistenceSingleton.__instance
__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "gpsPersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import json
import os
from datetime import datetime

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service, ServiceDB


Logs = LogsSingleton()


class _GPSPersistence(Service, ServiceDB):
    DB_NAME = "DB_gps.db"
    _table_name: str = "GPS"
    _list_fields: list = ["id", "coordenadas", "road_name", "municipio", "provincia", "date_create", "date_update"]
    _list_fields_type: list = ["INTEGER", "JSON", "VARCHAR(50)", "VARCHAR(20)", "VARCHAR(20)", "TIMESTAMP", "TIMESTAMP"]
    _primary_key: str = "id AUTOINCREMENT"

    POS_ID: int = 0
    POS_COORDENADAS: int = 1
    POS_ROAD_NAME: int = 2
    POS_MUNICIPIO: int = 3
    POS_PROVINCIA: int = 4
    POS_DATE_CREATE: int = 5
    POS_DATE_UPDATE: int = 6

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

    def insert_record_location(self, location_info: dict) -> bool:
        now: datetime = datetime.now()
        location_info[self._list_fields[self.POS_ID]] = "NULL"
        coords_json = json.dumps(location_info[self._list_fields[self.POS_COORDENADAS]])
        location_info[self._list_fields[self.POS_COORDENADAS]] = coords_json
        location_info[self._list_fields[self.POS_DATE_CREATE]] = now
        location_info[self._list_fields[self.POS_DATE_UPDATE]] = now
        return self.insert_record_db(self._table_name, self._list_fields, location_info)

    def get_last_gps_record(self):
        fields: list = list()
        params: list = list()
        for i in range(0, len(self._list_fields)):
            fields.append(self._list_fields[i])
        sql = f"SELECT {', '.join(fields)} FROM {self._table_name} ORDER BY id DESC LIMIT 1"
        res, record_list = self._db.query_sql(sql, tuple(params), fields)
        if not res or len(record_list) == 0:
            return []
        return record_list[0]

    def get_gps_record_since(self, since_time: datetime):
        fields: list = list()
        params: list = list()
        for i in range(0, len(self._list_fields)):
            fields.append(self._list_fields[i])
        params.append(since_time.strftime("%Y-%m-%d %H:%M:%S"))
        sql = f"SELECT {', '.join(fields)} FROM {self._table_name} WHERE date_create >= ?"
        res, record_list = self._db.query_sql(sql, tuple(params), fields)
        if not res or len(record_list) == 0:
            return []
        return record_list

    def get_gps_record_by_municipio(self, municipio: str):
        fields: list = list()
        params: list = list()
        for i in range(0, len(self._list_fields)):
            fields.append(self._list_fields[i])
        params.append(municipio)
        sql = f"SELECT {', '.join(fields)} FROM {self._table_name} WHERE municipio = ?"
        res, record_list = self._db.query_sql(sql, tuple(params), fields)
        if not res or len(record_list) == 0:
            return []
        return record_list

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
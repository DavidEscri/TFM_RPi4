__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "roadsPersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os
from shapely.geometry import Point, shape
import json

from tfm_muaii_rpi4.Utils.geolocation.geoUtils import Coordinates
from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service, ServiceDB

Logs = LogsSingleton()


class _MunicipiosPersistence(Service, ServiceDB):
    DB_NAME = "DB_municipios_cv.db"

    _table_name: str = "MUNICIPIOS"
    _list_fields: list = ["id", "name", "provincia", "municipio", "geometry"]
    _list_fields_type: list = ["INTEGER", "VARCHAR(50)", "VARCHAR(20)", "VARCHAR(50)", "JSON"]
    _primary_key: str = "id AUTOINCREMENT"

    POS_ID: int = 0
    POS_NAME: int = 1
    POS_PROVINCIA: int = 2
    POS_MUNICIPIO: int = 3
    POS_GEOMETRY: int = 4

    def __init__(self):
        Service.__init__(self, __info__, is_thread=False)
        try:
            env = EnvSingleton()
            db_path = env.get_path(env.DB_path)
            ServiceDB.__init__(self, self.DB_NAME, db_path)
            self._municipios: list = []
            self.__current_provincia: str = ""
            self.__current_municipio: str = ""
        except Exception as e:
            super().critical_error(e, "init")

    def start(self):
        try:
            super().start()
            if not os.path.isfile(self.path_db):
                raise Exception(f"No existe la base de datos {self.path_db}")
            self.__load_municipios()
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def __load_municipios(self):
        fields: list = list()
        params: list = list()
        fields.append(self._list_fields[self.POS_ID])
        fields.append(self._list_fields[self.POS_GEOMETRY])
        sql = f"SELECT {', '.join(fields)} FROM {self._table_name}"
        res, record_list = self._db.query_sql(sql, tuple(params), fields)
        self._municipios = [(row[fields[0]], shape(json.loads(row[fields[1]]))) for row in record_list]

    def get_record_municipio(self, coordinates: Coordinates):
        fields: list = list()
        fields.append(self._list_fields[self.POS_NAME])
        fields.append(self._list_fields[self.POS_PROVINCIA])
        fields.append(self._list_fields[self.POS_MUNICIPIO])
        params: list = list()
        point = Point(coordinates.get_coordinates()[::-1])
        for municipio_id, geom in self._municipios:
            if geom.contains(point):
                params.append(municipio_id)
                sql = f"SELECT {', '.join(fields)} FROM {self._table_name} WHERE id = ?"
                res, record_list = self._db.query_sql(sql, tuple(params), fields)
                self.__current_municipio = record_list[0]
                self.__current_provincia = record_list[0]["provincia"]
                return self.__current_municipio

    def get_current_municipio(self):
        return self.__current_municipio

    def get_current_provincia(self):
        return self.__current_provincia


class MunicipiosPersistenceSingleton:
    __instance = None

    def __new__(cls):
        if MunicipiosPersistenceSingleton.__instance is None:
            MunicipiosPersistenceSingleton.__instance = _MunicipiosPersistence()
        return MunicipiosPersistenceSingleton.__instance
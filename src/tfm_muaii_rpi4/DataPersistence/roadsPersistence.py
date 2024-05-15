__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "roadsPersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
import json

from tfm_muaii_rpi4.Utils.geolocation.geoUtils import Coordinates
from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service, ServiceDB

Logs = LogsSingleton()


class _RoadsPersistence(Service, ServiceDB):
    DB_NAME_ALICANTE = "DB_roads_alicante.db"
    DB_NAME_VALENCIA = "db_roads_valencia.db"
    DB_NAME_CASTELLON = "db_roads_castellon.db"

    _table_name: str = "ROADS"
    _list_fields: list = ["id", "tipo_tramo", "calzada", "carriles", "sentido", "clase", "tipo_via", "nombre",
                          "nombre_alt", "geometry"]
    _list_fields_type: list = ["INTEGER", "VARCHAR(20)", "VARCHAR(20)", "INTEGER", "VARCHAR(20)", "VARCHAR(30)",
                               "VARCHAR(30)", "VARCHAR(100)", "JSON"]
    _primary_key: str = "id AUTOINCREMENT"

    POS_ID: int = 0
    POS_TIPO_TRAMP: int = 1
    POS_CALZADA: int = 2
    POS_CARRILES: int = 3
    POS_SENTIDO: int = 4
    POS_CLASE: int = 5
    POS_TIPO_VIA: int = 6
    POS_NOMBRE: int = 7
    POS_NOMBRE_ALT: int = 8
    POS_GEOMETRY: int = 9

    def __init__(self, db_name):
        Service.__init__(self, __info__, is_thread=False)
        try:
            if db_name not in (self.DB_NAME_ALICANTE, self.DB_NAME_VALENCIA, self.DB_NAME_CASTELLON):
                raise Exception(f"El nombre {db_name} no es una base de datos correcta para carreteras")
            env = EnvSingleton()
            db_path = env.get_path(env.DB_path)
            ServiceDB.__init__(self, db_name, db_path)
        except Exception as e:
            super().critical_error(e, "init")

    def start(self):
        try:
            super().start()
            if not os.path.isfile(self.path_db):
                raise Exception(f"No existe la base de datos {self.path_db}")
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def get_record_by_coordinates(self, coordinates: Coordinates):
        fields: list = list()
        params: list = list()
        for i in range(0, len(self._list_fields)):
            fields.append(self._list_fields[i])
        params.append(coordinates)
        punto = Point(coordinates.get_coordinates())



class RoadPersistenceSingleton:
    __instance = None

    def __new__(cls, db_name):
        if RoadPersistenceSingleton.__instance is None:
            RoadPersistenceSingleton.__instance = _RoadsPersistence(db_name)
        return RoadPersistenceSingleton.__instance
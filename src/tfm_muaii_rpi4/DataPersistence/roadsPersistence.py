__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "roadsPersistence"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os
import time
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree
import json

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service, ServiceDB

Logs = LogsSingleton()


class RoadsDB:
    DB_NAME_ALICANTE = "DB_roads_alicante.db"
    DB_NAME_VALENCIA = "db_roads_valencia.db"
    DB_NAME_CASTELLON = "db_roads_castellon.db"


class _RoadsPersistence(Service, ServiceDB):

    _table_name: str = "ROADS"
    _list_fields: list = ["id", "carriles", "sentido", "clase", "tipo_via", "nombre", "geometry"]
    _list_fields_type: list = ["INTEGER", "INTEGER", "VARCHAR(20)", "VARCHAR(30)", "VARCHAR(20)", "VARCHAR(50)", "JSON"]
    _primary_key: str = "id AUTOINCREMENT"

    POS_ID: int = 0
    POS_CARRILES: int = 1
    POS_SENTIDO: int = 2
    POS_CLASE: int = 3
    POS_TIPO_VIA: int = 4
    POS_NOMBRE: int = 5
    POS_GEOMETRY: int = 6

    def __init__(self, db_name):
        Service.__init__(self, __info__, is_thread=False)
        try:
            if db_name not in (RoadsDB.DB_NAME_ALICANTE, RoadsDB.DB_NAME_VALENCIA, RoadsDB.DB_NAME_CASTELLON):
                raise Exception(f"El nombre {db_name} no es una base de datos correcta para carreteras")
            self.DB_NAME = db_name
            env = EnvSingleton()
            self.__line_strings: list = []
            self.__strtree: STRtree = None
            db_path = env.get_path(env.DB_path)
            ServiceDB.__init__(self, db_name, db_path)
        except Exception as e:
            super().critical_error(e, "init")

    def start(self):
        try:
            super().start()
            if not os.path.isfile(self.path_db):
                raise Exception(f"No existe la base de datos {self.path_db}")
            self.__load_road_db()
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def __load_road_db(self) -> None:
        #TODO: Cargar la base de datos que toca, por como lo tenía hecho se tendría que hacer en el arranque, analizar
        # si realmente tiene que ser así

        #TODO: Quizás debería hacerlo a nivel de gpsController, pero entonces cada vez que cree una instancia de esta
        # base de datos voy a tener que pasarle el nombre de la base de datos. ¿Utilizar nombre de provincia? Si ya está
        # cargada, se puede utilizar, si no lo está o es diferente, entonces se vuelve a cargar.
        Logs.get_logger().debug(f"Iniciando carga de geometrias de {self.DB_NAME}", extra=__info__)
        init_load_db_time = time.time()
        fields: list = list()
        params: list = list()
        fields.append(self._list_fields[self.POS_ID])
        fields.append(self._list_fields[self.POS_GEOMETRY])
        sql = f"SELECT {', '.join(fields)} FROM {self._table_name}"
        res, record_list = self._db.query_sql(sql, tuple(params), fields)
        self.__line_strings = [(row[fields[0]], LineString(json.loads(row[fields[1]])["coordinates"])) for row in record_list]
        self.__strtree = STRtree([geom for _, geom in self.__line_strings])
        load_db_time = time.time() - init_load_db_time
        Logs.get_logger().debug(f"Carga de geometrias de {self.DB_NAME} cargada en {load_db_time:.2f} s", extra=__info__)

    def get_record_by_coordinates(self, coords: tuple) -> dict:
        Logs.get_logger().debug(f"Obteniendo carretera actual...", extra=__info__)
        init_get_road_time = time.time()
        while self.__strtree is None:
            Logs.get_logger().warning("Esperando carga de carreteras, proxima intento en 10 segundos", extra=__info__)
            time.sleep(10)
        fields: list = list()
        params: list = list()
        for i in range(0, len(self._list_fields)):
            fields.append(self._list_fields[i])
        point = Point(coords)
        nearest_line_index = self.__strtree.nearest(point)
        nearest_road_index = next(id for id, geom in self.__line_strings if geom.equals(self.__line_strings[nearest_line_index][1]))
        params.append(nearest_road_index)
        sql = f"SELECT {', '.join(fields)} FROM {self._table_name} WHERE id = ?"
        res, record_list = self._db.query_sql(sql, tuple(params), fields)
        get_road_time = time.time() - init_get_road_time
        Logs.get_logger().debug(f"Carretera actual obtenida en {get_road_time:.2f} s", extra=__info__)
        return record_list[0]


class RoadPersistenceSingleton:
    __instance = None

    def __new__(cls, db_name):
        if RoadPersistenceSingleton.__instance is None:
            RoadPersistenceSingleton.__instance = _RoadsPersistence(db_name)
        return RoadPersistenceSingleton.__instance
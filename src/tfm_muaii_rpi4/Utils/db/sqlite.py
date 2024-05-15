__author__ = "Jose David Escribano Orts"
__subsystem__ = "Utils"
__module__ = "sqlite"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import sqlite3
from sqlite3 import Connection
from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class SqlUtils:

    def __init__(self, path: str):
        self._path = path

    def insert_sql(self, sql: str, params: tuple) -> bool:
        connection: Connection = None
        check: bool = False
        try:
            connection = sqlite3.connect(self._path)
            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()
            check = True
        except Exception as ex:
            Logs.get_logger().error("Error al insertar en la base de datos: %s", ex, exc_info=True, extra=__file__)
        finally:
            if connection:
                connection.close()
        return check

    def update_sql(self, sql: str, params: tuple) -> bool:
        connection: Connection = None
        check: bool = False
        try:
            connection = sqlite3.connect(self._path)
            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()
            check = True
        except Exception as ex:
            Logs.get_logger().error("Error al actualizar en la base de datos: %s", ex, exc_info=True, extra=__file__)
        finally:
            if connection:
                connection.close()
        return check

    def query_sql(self, sql: str, params: tuple, list_field: list) -> (bool, list):
        connection: Connection = None
        check = [False, None]
        list_res: list = []
        try:
            connection = sqlite3.connect(self._path)
            cursor = connection.cursor()
            cursor.execute(sql, params)
            register = cursor.fetchall()
            for i in register:
                counter = 0
                res = dict()
                for j in list_field:
                    res[j] = i[counter]
                    counter += 1
                list_res.append(res)
            check = [True, list_res]
        except Exception as ex:
            Logs.get_logger().error("Error al obtener el registro desde la DB: %s", ex, exc_info=True,
                                    extra=__file__)
        finally:
            if connection:
                connection.close()
        return check[0], check[1]

    def create_db(self, sql: str) -> bool:
        check = False
        connection: Connection = None
        try:
            connection = sqlite3.connect(self._path)
            cursor = connection.cursor()
            cursor.execute(sql)
            connection.commit()
            check = True
        except Exception as ex:
            Logs.get_logger().error("Error al crear DB: %s", ex, exc_info=True, extra=__file__)
        finally:
            if connection:
                connection.close()
        return check

    def get_conn(self) -> Connection:
        return sqlite3.connect(self._path)
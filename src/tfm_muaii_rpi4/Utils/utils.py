__author__ = "Jose David Escribano Orts"
__subsystem__ = "Utils"
__module__ = "utils"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import time
import os
import socket
from threading import Thread, Event

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Utils.db.sqlite import SqlUtils
from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class Service:

    def __init__(self, info: dict, is_thread: bool = False):
        self._info = info
        self._is_thread = is_thread
        self._stop_thread = None
        self._thread_srv: Thread = None
        self.sleep_period = 0
        if self._is_thread:
            self.sleep_period = 1
            self._stop_thread = Event()

    def start(self):
        if self._is_thread:
            if not self._get_run_status():
                self._stop_thread.clear()
                self._thread_srv = Thread(target=self._run)
                self._thread_srv.daemon = True
                self._thread_srv.name = f"THREAD_{self._info['module_name']}"
                Logs.get_logger().debug("Levantando en servicio %s hilo %s", self._info["module_name"],
                                        self._thread_srv.name, extra=self._info)
                self._thread_srv.start()
        else:
            Logs.get_logger().debug("Servicio %s iniciado", self._info["module_name"], extra=self._info)

    def _run(self):
        pass

    def sleep_period(self):
        count: int = 0
        while not (self.need_stop() or count > self.sleep_period):
            time.sleep(1)
            count = count + 1

    def stop(self):
        if self._is_thread:
            self._stop_thread.set()
            self._thread_srv.join(self.sleep_period + 1)
            if self._thread_srv.is_alive():
                Logs.get_logger().warning("No fue posible la salida de servicio %s hilo %s", self._info["module_name"],
                                       self._thread_srv.name, extra=self._info)
            else:
                Logs.get_logger().info("Salida de servicio %s hilo %s", self._info["module_name"],
                                       self._thread_srv.name, extra=self._info)
        else:
            Logs.get_logger().info("Servicio %s parado", self._info["module_name"], extra=self._info)

    def _get_run_status(self):
        """
        Devuelve True si el módulo se está ejecutando
        """
        if self._thread_srv is not None:
            return self._thread_srv.is_alive()
        else:
            return False

    def need_stop(self) -> bool:
        return self._stop_thread.is_set()

    def critical_error(self, err, funct: str) -> None:
        """
        Reporta un error crítico al servicio
        :return:
        """
        Logs.get_logger().critical("Error critico en función %s en el servicio : %s", funct, err,
                                   exc_info=True, extra=self._info)


class ServiceDB:
    def __init__(self, db_name: str, db_path: str = None):

        if db_path is not None:
            path = db_path
        else:
            env = EnvSingleton()
            path = env.get_path(env.db_path)
        if not os.path.exists(path):
            os.makedirs(path)
        self.path_db = os.path.join(path, db_name)
        self._db = SqlUtils(self.path_db)

    def create_table(self, table_name: str, list_fields: list, list_fields_type: list, primary_key: str) -> bool:
        fields: list = list()
        for i in range(0, len(list_fields)):
            fields.append(f"{list_fields[i]} {list_fields_type[i]}")
        fields.append(f"PRIMARY KEY ({primary_key})")
        sql: str = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(fields)})"
        result: bool = self._db.create_db(sql)
        if result:
            Logs.get_logger().debug("Tabla %s creada en %s", table_name, self.path_db, extra=__info__)
        else:
            Logs.get_logger().error("Error al crear tabla %s creada en %s", table_name, self.path_db, extra=__info__)
        return result

    @staticmethod
    def validate_record(list_fields: list, record: dict) -> bool:
        if not all(item in list_fields for item in list(record.keys())):
            return False
        else:
            return True

    def insert_record_db(self, table_name: str, list_fields: list, record: dict) -> (bool, int):
        """
        Método abstracto para insertar un registro en la DB
        """
        if not self.validate_record(list_fields, record):
            Logs.get_logger().error("Parámetros de entrada en el insert de %s no son correctos", table_name,
                                    extra=__info__)
            return False, 0

        fields: list = list()
        params: list = list()
        lq: list = list()

        for i in range(0, len(list_fields)):
            fields.append(list_fields[i])
            if record[list_fields[i]] == "NULL":
                lq.append("NULL")
            else:
                params.append(record[list_fields[i]])
                lq.append("?")

        sql: str = f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({', '.join(lq)})"
        return self._db.insert_sql(sql, tuple(params))


def internet_access(host="8.8.8.8", port=53, timeout=1):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False
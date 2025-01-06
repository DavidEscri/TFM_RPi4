__author__ = "Jose David Escribano Orts"
__subsystem__ = "GPSController"
__module__ = "routeMapGenerator"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import datetime
import json
import os

import folium

from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton, ContextVarsConst
from tfm_muaii_rpi4.DataPersistence.gpsPersistence import GpsPersistenceSingleton
from tfm_muaii_rpi4.DataPersistence.municipiosPersistence import MunicipiosPersistenceSingleton
from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service

Logs = LogsSingleton()


class _RouteMapGenerator(Service):

    def __init__(self):
        super().__init__(__info__, is_thread=True)
        self.context_vars = ContextVarsMgrSingleton()
        self.gps_pers = GpsPersistenceSingleton()
        self.municipios_pers = MunicipiosPersistenceSingleton()
        self.env = EnvSingleton()
        self.__last_generated_time = datetime.datetime.now()
        self.__last_generated_municipio = ""
        self.__route_map_generation_period = datetime.timedelta(minutes=30)
        self.__route_map_path = self.env.get_path(self.env.route_map_path)
        self.sleep_period = 60

    def start(self):
        try:
            self.__clean_old_route_maps()
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def __clean_old_route_maps(self, days: int = 7):
        try:
            if not os.path.exists(self.__route_map_path):
                os.makedirs(self.__route_map_path)
                return
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            cutoff_timestamp = cutoff_date.timestamp()
            for file in os.listdir(self.__route_map_path):
                if file.startswith("route_map") and file.endswith(".html"):
                    file_path = os.path.join(self.__route_map_path, file)
                    file_creation_time = os.path.getctime(file_path)
                    if file_creation_time < cutoff_timestamp:
                        os.remove(file_path)
        except Exception as e:
            Logs.get_logger().error(f"Error en el limpiado de mapas de rutas generadores: {e}", extra=__info__)

    def _run(self):
        while not super().need_stop() and not self.context_vars.get_context_var(ContextVarsConst.GEOLOCATION_READY):
            Logs.get_logger().warning("Esperando servicio de geolocalización para iniciar generación de mapa de rutas...",
                                      extra=__info__)
            super().sleep_period()
        while not super().need_stop():
            try:
                if not self.context_vars.get_context_var(ContextVarsConst.GEOLOCATION_READY):
                    Logs.get_logger().warning("Geolocalización no disponible. Esperando recuperación...", extra=__info__)
                    self.__last_generated_time = datetime.datetime.now()  # Reiniciar el temporizador
                    self.current_municipio = None
                    super().sleep_period()
                if self.__check_time_limit_generation():
                    self.__generate_route_map_by_time()
                    super().sleep_period()
                    continue
                Logs.get_logger().info("No se ha superado el tiempo límite entre generación de mapas", extra=__info__)
                if self.__check_municipio_generation():
                    self.__generate_route_map_by_municipio()
                    super().sleep_period()
                    continue
                Logs.get_logger().info(f"Se sigue viajando por el municipio {self.__last_generated_municipio}", extra=__info__)
                super().sleep_period()
            except Exception as e:
                Logs.get_logger().error(f"Error hilo generatión de mapa de rutas: {e}", extra=__info__)

    def __check_time_limit_generation(self):
        now = datetime.datetime.now()
        time_elapsed = now - self.__last_generated_time
        return time_elapsed > self.__route_map_generation_period

    def __check_municipio_generation(self):
        current_municipio = self.municipios_pers.get_current_municipio()
        return self.__last_generated_municipio != current_municipio

    def __generate_route_map_by_time(self):
        Logs.get_logger().info("Se ha superado el tiempo límite entre mapas, generando nuevo mapa de rutas",
                               extra=__info__)
        now = datetime.datetime.now()
        since_time: datetime = now - self.__route_map_generation_period
        last_time_coordinates = self.gps_pers.get_gps_record_since(since_time)
        if len(last_time_coordinates) == 0:
            Logs.get_logger().warning("No se encontraron coordenadas en el último tramo de tiempo", extra=__info__)
            return
        self.__generate_route_map(last_time_coordinates)
        self.__last_generated_time = now

    def __generate_route_map_by_municipio(self):
        Logs.get_logger().info("El municipio ha cambiado, generando nuevo mapa de rutas", extra=__info__)
        last_municipio_coordinates = self.gps_pers.get_gps_record_by_municipio(self.__last_generated_municipio)
        if len(last_municipio_coordinates) == 0:
            Logs.get_logger().warning(f"No se encontraron coordenadas del municipio {self.__last_generated_municipio}",
                                      extra=__info__)
            self.__last_generated_municipio = self.municipios_pers.get_current_municipio()
            return
        self.__generate_route_map(last_municipio_coordinates)
        self.__last_generated_municipio = self.municipios_pers.get_current_municipio()

    def __generate_route_map(self, gps_records: list):
        map_center_coords = json.loads(gps_records[0]["coordenadas"])
        route_map = folium.Map(location=map_center_coords, zoom_start=16)
        all_route_coordinates = [json.loads(coords["coordenadas"]) for coords in gps_records]
        folium.PolyLine(all_route_coordinates, color="blue", weight=2.5, opacity=1).add_to(route_map)
        for route_coordinate in all_route_coordinates:
            folium.Marker(location=route_coordinate).add_to(route_map)
        file_name = f"route_map_{self.__last_generated_municipio}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        route_map_file = os.path.join(self.__route_map_path, file_name)
        route_map.save(route_map_file)
        Logs.get_logger().info(f"Generado mapa de ruta {file_name}", extra=__info__)


class RouteMapGeneratorSingleton:
    __instance = None

    def __new__(cls):
        if RouteMapGeneratorSingleton.__instance is None:
            RouteMapGeneratorSingleton.__instance = _RouteMapGenerator()
        return RouteMapGeneratorSingleton.__instance
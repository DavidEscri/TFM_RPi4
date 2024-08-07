__author__ = "Jose David Escribano Orts"
__subsystem__ = "Utils"
__module__ = "geoUtils"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import time
import datetime
import os
import json
import geopy.distance
from geopy.geocoders import Nominatim

from tfm_muaii_rpi4.DataPersistence.roadsPersistence import RoadsDB
from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton


Logs = LogsSingleton()


class Coordinates:
    def __init__(self, latitude: float, longitude: float):
        self.data: dict = {
            "coordinates": (latitude, longitude),
            "timestamp": time.time()
        }

    def get_coordinates(self) -> tuple:
        return self.data["coordinates"]

    def valid_coordinates(self) -> bool:
        return self.get_coordinates() != (0, 0)

    def get_timestamp(self) -> datetime:
        return self.data["timestamp"]


class GeoUtils:
    def get_online_max_speed_and_location(self, coordenadas: Coordinates) -> (int, str):
        """
        Obtención de la máxima velocidad en km/h de una localizacicón definida por la libreria de geopy
        :param coordenadas: Coordenadas de la localización
        :return: Velocidad en km/h
        """
        max_speed: int = 0
        location_info: str = ""
        if not coordenadas.valid_coordinates():
            return max_speed, location_info
        geolocator = Nominatim(user_agent="my_geocoder")
        location = geolocator.reverse(coordenadas.get_coordinates(), language='es')
        if location:
            road_type = self.__get_online_road_type(location)
            max_speed = self.__convert_online_road_speed_limit(road_type)
            if "address" in location.raw:
                road_adress = location.raw["address"]
                road_name = road_adress["road"] if "road" in road_adress else ""
                ciudad = road_adress["city"] if "city" in road_adress else road_adress["town"]
                provincia = road_adress["state_district"] if "state_district" in road_adress else road_adress["province"]
                location_info = f"{road_name}, {ciudad} ({provincia})"
                Logs.get_logger().debug(f"La velocidad máxima para {road_name} ubicado en {ciudad} ({provincia}) es: "
                                       f"{max_speed} km/h", extra=__info__)
        return max_speed, location_info

    def get_offline_max_speed_and_location(self, road_info: dict) -> (int, str):
        #TODO: En el arranque se tendrá que cargar fichero con info de carreteras de la comunidad valenciana y obtener
        # de ahí la información
        road_type: str = road_info["tipo_via"]
        max_speed: int = self.__convert_offline_road_speed_limit(road_info["clase"], road_type)
        road_name: str = road_info["nombre"].capitalize()
        municipio: str = road_info["municipio"].capitalize()
        provincia: str = road_info["provincia"].capitalize()
        location_info = f"{road_type.capitalize()} {road_name}, {municipio} ({provincia})"
        Logs.get_logger().debug(f"La velocidad máxima para {road_type.capitalize()} {road_name} ubicado en {municipio} "
                                f"({provincia}) es: {max_speed} km/h", extra=__info__)
        return max_speed, location_info

    @staticmethod
    def __convert_offline_road_speed_limit(road_class: str, road_type: str) -> int:
        if road_class == "Carretera convencional":
            carretera_conv = {
                {"Carretera", "CTRA", "Red TenT Global", "CARRE"}: 90,
                {"CALLE", "Vial", "AVDA", "C", "C/", "PG", "PL", "URB", "PLAZA", "Desconocido", "AVGDA",
                 "VIA", "GRUP", "POLIG", "PDA", "LUGAR", "TRSSI", "RONDA", "PLCET", "PLAÇA", "PASEO",
                 "PTGE"}: 50,
                {"BARRO", "CMNO", "camino", "PRAJE", "ALDEA", "CÑADA"}: 30,
                {"Vía verde", "SEND", "Vial bici", "SENDA", "VREDA"}: 20
            }
            for roads, velocidad in carretera_conv.items():
                if road_type in roads:
                    return velocidad
            return 0

        if road_class == "Carretera multicarril":
            carretera_multi = {
                {"Carretera", "CTRA", "Red TenT Global"}: 100,
                {"AVDA", "C/", "AV", "PONT", "C", "PG", "CALLE"}: 50
            }
            for roads, velocidad in carretera_multi.items():
                if road_type in roads:
                    return velocidad
            return 0

        speed_limits = {
            "Autopista de peaje": 120,
            "Autopista libre / autovía": 120,
            "Camino": 30,
            "Senda": 20,
            "Carril bici": 20,
            "Urbano": 50
        }
        return speed_limits.get(road_class, 0)

    @staticmethod
    def __get_online_road_type(location: geopy.location.Location) -> str:
        """
        Obtención del tipo de carretera
        :param location: Localizacíon obtenida con la libreria de geopy
        :return: Tipo de carretera definido por Nominatim
        """
        road_type: str = ""
        if location:
            road_type = location.raw["type"]
        return road_type

    @staticmethod
    def __convert_online_road_speed_limit(road_type: str) -> int:
        """
        Obtención de la velocidad máxima a partir del tipo de carretera
        :param road_type: Tipo de carretera definido por Nominatim.
        :return: Velocidad máxima
        """
        speed_limits = {
            "motorway": 120,  # Autovía / Autopista
            "trunk": 100,  # Carretera convencional de doble calzada
            "primary": 90,  # Carretera convencional de un solo carril
            "secondary": 80,  # Carretera secundaria
            "tertiary": 70,  # Carretera terciaria
            "unclassified": 50,  # Carretera no clasificada
            "residential": 30,  # Zona residencial
            "service": 20,  # Vía de servicio
            "school": 20,  # Cerca de escuales
        }
        # Devolver la velocidad máxima según el tipo de carretera
        return speed_limits.get(road_type, 0)

    def calculate_speed(self, last_coordinates: Coordinates, current_coordinates: Coordinates) -> int:
        """
        Se calcula la velocidad en km/h a la que se está circulando a partir de dos coordenadas.
        :param last_coordinates: Últimas coordenadas obtenidas.
        :param current_coordinates: Coordenadas actuales.
        :return: Velocidad actual
        """
        if not isinstance(last_coordinates, Coordinates) and not isinstance(current_coordinates, Coordinates):
            return None
        distance = geopy.distance.geodesic(last_coordinates.get_coordinates(),
                                           current_coordinates.get_coordinates()).m
        time_difference = current_coordinates.get_timestamp() - last_coordinates.get_timestamp()
        if time_difference == 0:
            return 0
        speed = distance / time_difference
        return self.__convert_ms_to_kmh(speed)

    @staticmethod
    def __convert_ms_to_kmh(speed: float) -> int:
        """
        Conversión de velocidad de m/s a km/h
        :param speed: Velocidad en metros por segundo
        :return: Velocidad en kilometros por hora
        """
        return round(speed * 3.6)

    @staticmethod
    def convert_provincia_to_road_db(provincia: str):
        pronvicia_db = {
            "Alicante": RoadsDB.DB_NAME_ALICANTE,
            "Valencia": RoadsDB.DB_NAME_VALENCIA,
            "Castellón": RoadsDB.DB_NAME_CASTELLON
        }
        return pronvicia_db.get(provincia, None)

    # def is_speed_limit_exceeded(self, last_coordinates: Coordinates, current_coordinates: Coordinates) -> bool:
    #     """
    #     Se calcula la velocidad a la que se está circulando, y la compara con la velocidad máxima permitida para la
    #     localización actual.
    #     :param last_coordinates: Últimas coordenadas obtenidas.
    #     :param current_coordinates: Coordenadas actuales.
    #     :return: Booleano si la velocidad actual es superior a la máxima permitida
    #     """
    #     max_speed, _ = self.get_online_max_speed_and_location(current_coordinates)
    #     current_speed = self.calculate_speed(last_coordinates, current_coordinates)
    #     print(f"Velocidad actual: {current_speed} km/h")
    #     return current_speed > max_speed


if __name__ == "__main__":
    # Autopista del Mediterráneo, Daya Nueva, La Vega Baja del Segura, Alicante, Comunidad Valenciana, 03106, España
    #latitude = 38.1194
    #longitude = -0.7785

    # coordenadas: Coordinates = Coordinates(38.28931, -0.70968)
    # speed_limit = get_coordinates_data(coordenadas)
    geo_utils = GeoUtils()
    coords1 = Coordinates(38.11219, -0.78666)
    time.sleep(1)  # Simular el paso de un segundo
    coords2 = Coordinates(38.11254, -0.78696)
    if geo_utils.is_speed_limit_exceeded(coords1, coords2):
        print("Velocidad límite superada")
    # speed = geo_utils.calculate_speed(coords1, coords2)
    # speed_limit_2 = get_coordinates_data(coords1)
    # print(speed)

    coords1 = Coordinates(38.11792, -0.77826)
    time.sleep(1)
    coords2 = Coordinates(38.11828, -0.77834)
    if geo_utils.is_speed_limit_exceeded(coords1, coords2):
        print("Velocidad límite superada")
    # speed = geo_utils.calculate_speed(coords1, coords2)
    # speed_limit_3 = get_coordinates_data(coords1)
    # print(speed)

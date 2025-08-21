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


class RouteMapBuilder:
    def __init__(self, gps_records: list, zoom_start: int = 16, line_color: str = "blue", line_weight: float = 2.5,
                 line_opacity: float = 1.0):
        if len(gps_records) == 0:
            raise ValueError("La lista de registros GPS no puede estar vacío")
        self.gps_records = gps_records
        self.zoom_start = zoom_start
        self.line_color = line_color
        self.line_weight = line_weight
        self.line_opacity = line_opacity

    def generate(self, output_path: str):
        map_center_coords = json.loads(self.gps_records[0]["coordenadas"])
        route_map = folium.Map(location=map_center_coords, zoom_start=self.zoom_start)
        all_route_coordinates = [json.loads(record["coordenadas"]) for record in self.gps_records]
        folium.PolyLine(all_route_coordinates, color=self.line_color, weight=self.line_weight,
                        opacity=self.line_opacity).add_to(route_map)
        for index, gps_record in enumerate(self.gps_records):
            coords: dict = all_route_coordinates[index]
            html: str = self._build_popup_html(gps_record, index)
            iframe: folium.IFrame = folium.IFrame(html=html, width="380px", height="260px")
            popup: folium.Popup = folium.Popup(iframe, max_width=520)
            marker: folium.Marker = folium.Marker(location=coords, popup=popup, tooltip=f"Clic para ver registro histórico #{index+1}")
            marker.add_to(route_map)

            # Guardar HTML
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        route_map.save(output_path)

    def _build_popup_html(self, gps_record: dict, index: int) -> str:
        record_datetime: datetime = gps_record["date_create"]
        record_context: dict = json.loads(gps_record["context"])

        # Construir tabla HTML con el mismo orden de variables para cada punto
        html_parts = []
        html_parts.append(f"<div><strong>Registro #{index+1}</strong></div>")
        html_parts.append(f"<div style='font-size:12px;color:#444;'><em>Fecha: </em> {record_datetime}</div>")
        html_parts.append("<hr style='margin:6px 0;'/>")
        html_parts.append("<div style='max-height:260px;overflow:auto;'>")
        html_parts.append("<table style='border-collapse:collapse;width:100%;font-size:12px;'>")
        html_parts.append("<thead><tr>"
                          "<th style='text-align:left;padding:4px;border-bottom:1px solid #ccc;'>Estado</th>"
                          "<th style='text-align:left;padding:4px;border-bottom:1px solid #ccc;'>Descripción</th>"
                          "</tr></thead>")
        html_parts.append("<tbody>")

        for context_var_name, context_var_value in record_context.items():
            if context_var_name not in {ContextVarsConst.PERSONAS, ContextVarsConst.GEOLOCATION_READY, ContextVarsConst.MAL_ESTADO_CARRETERA}:
                continue
            if context_var_name == ContextVarsConst.PERSONAS:
                personas_text: str = f"{context_var_value} de {record_context[ContextVarsConst.MAX_PERSONAS]} pasajeros"
                html_parts.append(
                    "<tr>"
                    f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Aforo </td>"
                    f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> {personas_text} </td>"
                    "</tr>"
                )
            elif context_var_name == ContextVarsConst.GEOLOCATION_READY:
                geolocation_text: str = "OK" if context_var_value else "Pendiente de obtener ubicación"
                if context_var_value is False:
                    html_parts.append(
                        "<tr>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Geolocalización </td>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> {geolocation_text} </td>"
                        "</tr>"
                    )
                    continue
                # Estado Geolocalización
                html_parts.append(
                    "<tr>"
                    f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Geolocalización </td>"
                    f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> {geolocation_text} </td>"
                    "</tr>"
                )
                # Movimiento
                if record_context[ContextVarsConst.VEHICULO_PARADO] is True:
                    html_parts.append(
                        "<tr>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Vehículo </td>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> Parado </td>"
                        "</tr>"
                    )
                else:
                    # Velocidad
                    velocidad_text = f"{record_context[ContextVarsConst.VELOCIDAD_ACTUAL]} km/h (max. {record_context[ContextVarsConst.VELOCIDAD_MAXIMA]} km/h)"
                    html_parts.append(
                        "<tr>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Velocidad </td>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> {velocidad_text} </td>"
                        "</tr>"
                    )
                html_parts.append(
                    "<tr>"
                    f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Satelites GNSS </td>"
                    f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> {str(record_context[ContextVarsConst.SATELITES_GNSS])} </td>"
                    "</tr>"
                )
                html_parts.append(
                    "<tr>"
                    f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Precisión GNSS </td>"
                    f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> {str(record_context[ContextVarsConst.PRECISION_GNSS])} </td>"
                    "</tr>"
                )
            elif context_var_name == ContextVarsConst.MAL_ESTADO_CARRETERA:
                carretera_text: str = "Mal estado" if context_var_value else "OK"
                if context_var_value is False:
                    html_parts.append(
                        "<tr>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Carretera </td>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> {carretera_text} </td>"
                        "</tr>"
                    )
                else:
                    html_parts.append(
                        "<tr>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;vertical-align:top;white-space:nowrap;'> Carretera </td>"
                        f"<td style='padding:4px;border-bottom:1px solid #eee;white-space:pre-wrap;'> {carretera_text} </td>"
                        "</tr>"
                    )

        html_parts.append("</tbody></table></div>")
        return "".join(html_parts)


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
                    self.__last_generated_municipio = ""
                    super().sleep_period()
                    continue
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

    # def __generate_route_map_old(self, gps_records: list):
    #     map_center_coords = json.loads(gps_records[0]["coordenadas"])
    #     route_map = folium.Map(location=map_center_coords, zoom_start=16)
    #     all_route_coordinates = [json.loads(coords["coordenadas"]) for coords in gps_records]
    #     folium.PolyLine(all_route_coordinates, color="blue", weight=2.5, opacity=1).add_to(route_map)
    #     for route_coordinate in all_route_coordinates:
    #         folium.Marker(location=route_coordinate).add_to(route_map)
    #     file_name = f"route_map_{self.__last_generated_municipio}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    #     route_map_file = os.path.join(self.__route_map_path, file_name)
    #     route_map.save(route_map_file)
    #     Logs.get_logger().info(f"Generado mapa de ruta {file_name}", extra=__info__)

    def __generate_route_map(self, gps_records: list):
        route_map: RouteMapBuilder = RouteMapBuilder(gps_records)
        municipio: str = self.__last_generated_municipio if len(self.__last_generated_municipio) > 0 else self.municipios_pers.get_current_municipio()
        file_name = f"route_map_{municipio}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        route_map_file = os.path.join(self.__route_map_path, file_name)
        route_map.generate(route_map_file)
        Logs.get_logger().info(f"Generado mapa de ruta {file_name}", extra=__info__)


class RouteMapGeneratorSingleton:
    __instance = None

    def __new__(cls):
        if RouteMapGeneratorSingleton.__instance is None:
            RouteMapGeneratorSingleton.__instance = _RouteMapGenerator()
        return RouteMapGeneratorSingleton.__instance
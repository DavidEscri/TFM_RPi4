from geopy.geocoders import Nominatim, OpenCage
import osmnx as osm
import requests


def get_speed_limit(lat, lon):
    geolocator = Nominatim(user_agent="my_geocoder")
    location = geolocator.reverse((lat, lon), language='es')

    if location:
        road_type = location.raw["type"]
        place_id = location.raw["place_id"]
        osm_id = location.raw["osm_id"]
        road_data = osm.geocode_to_gdf(str(place_id))
        max_speed = estimate_speed_limit(road_type)
        if "address" in location.raw:
            road_adress = location.raw["address"]
            road_name = road_adress["road"]
            #barrio = road_adress["suburb"]
            ciudad = road_adress["city"]
            provincia = road_adress["state_district"]
            #comunidad = road_adress["state"]
            pais = road_adress["country"]
            print(f"La velocidad máxima para {road_name} ubicado en {ciudad} provincia de {provincia} ({pais}) es: "
                  f"{max_speed} km/h")
        return max_speed
    else:
        print("Unable to reverse geocode coordinates.")

    return None


def estimate_speed_limit(road_type: str):
    # Definir velocidades máximas según el tipo de carretera en España
    speed_limits = {
        'motorway': 120,  # Autovía/Autopista
        'trunk': 100,  # Carretera convencional de doble calzada
        'primary': 90,  # Carretera convencional de un solo carril
        'secondary': 70,  # Carretera convencional de un solo carril
        'residential': 30  # Zona residencial
    }
    # Devolver la velocidad máxima según el tipo de carretera
    return speed_limits.get(road_type, None)

def calculate_speed(last_coordinates, current_coordinates):
    pass

# Autopista del Mediterráneo, Daya Nueva, La Vega Baja del Segura, Alicante, Comunidad Valenciana, 03106, España
#latitude = 38.1194
#longitude = -0.7785

#
latitude = 38.28931
longitude = -0.70968
speed_limit = get_speed_limit(latitude, longitude)

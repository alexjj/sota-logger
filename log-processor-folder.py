import adif_io
import json
import math
import sys
from pathlib import Path
import requests

def get_sota_latlon(summit_code):
    url = f"https://api-db2.sota.org.uk//api/summits/{summit_code}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("latitude"), data.get("longitude")
    except requests.RequestException:
        return None, None

def grid_to_latlon(maiden):
    maiden = maiden.strip().upper()
    N = len(maiden)
    if not ((8 >= N >= 2) and (N % 2 == 0)):
        raise ValueError("Maidenhead locator requires 2-8 characters, even number of characters")

    Oa = ord("A")
    lon = -180.0 + (ord(maiden[0]) - Oa) * 20
    lat = -90.0 + (ord(maiden[1]) - Oa) * 10

    if N >= 4:
        lon += int(maiden[2]) * 2
        lat += int(maiden[3]) * 1
    if N >= 6:
        lon += (ord(maiden[4]) - Oa) * 5.0 / 60
        lat += (ord(maiden[5]) - Oa) * 2.5 / 60
    if N >= 8:
        lon += int(maiden[6]) * 5.0 / 600
        lat += int(maiden[7]) * 2.5 / 600

    return lat, lon

def calculate_arc_length(lat1, lon1, alt1, lat2, lon2, alt2):
    """
    Calculate the circumference segment (arc length) between two mountain summits.

    Parameters:
        lat1, lon1: Latitude and Longitude of the first summit in degrees.
        alt1: Altitude of the first summit in meters.
        lat2, lon2: Latitude and Longitude of the second summit in degrees.
        alt2: Altitude of the second summit in meters.

    Returns:
        Arc length in meters.
    """
    # Earth's equatorial and polar radii in meters
    a = 6378137.0  # in meters
    b = 6356752.3  # in meters

    # Convert latitudes and longitudes from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Calculate the radius of the Earth at a given latitude using the formula for an ellipsoid
    def earth_radius_at_latitude(lat):
        cos_lat = math.cos(lat)
        sin_lat = math.sin(lat)
        numerator = ((a**2) * (cos_lat)**2 + (b**2) * (sin_lat)**2)
        denominator = (cos_lat)**2 + ((b / a)**2) * (sin_lat)**2
        return math.sqrt(numerator / denominator)

    # Calculate the radii at the two latitudes
    radius1 = earth_radius_at_latitude(lat1_rad) + alt1
    radius2 = earth_radius_at_latitude(lat2_rad) + alt2

    # Calculate the central angle
    delta_lon = lon2_rad - lon1_rad
    central_angle = math.acos(math.sin(lat1_rad) * math.sin(lat2_rad) + math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))

    # Calculate the arc length
    arc_length = ((radius1 + radius2) / 2) * central_angle

    return arc_length/1000


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def adif_to_json(adif_file):
    records, _ = adif_io.read_from_file(str(adif_file))

    if not records:
        raise ValueError("ADIF file contains no records")

    first_record = records[0]
    my_callsign = first_record.get('STATION_CALLSIGN', '')
    my_locator = first_record.get('MY_GRIDSQUARE', '')
    my_sota = first_record.get('MY_SOTA_REF', '')
    date = first_record.get('QSO_DATE', '')
    if date:
        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    if my_sota:
        my_lat, my_lon = get_sota_latlon(my_sota)
    else:
        my_lat, my_lon = grid_to_latlon(my_locator) if my_locator else (None, None)

    qso_list = []
    for record in records:
        callsign = record.get('CALL')
        band = record.get('BAND')
        qth = record.get('QTH', '')
        grid = record.get('GRIDSQUARE', '')
        sota_ref = record.get('SOTA_REF', '')
        comment = record.get('COMMENT', '')

        if sota_ref:
            lat, lon = get_sota_latlon(sota_ref)
            distance = haversine(my_lat, my_lon, lat, lon) if my_lat and my_lon and lat and lon else None
        elif grid:
            lat, lon = grid_to_latlon(grid)
            distance = haversine(my_lat, my_lon, lat, lon) if my_lat and my_lon else None
        else:
            lat, lon, distance = None, None, None

        qso_list.append({

            "time": record.get('TIME_ON', ''),
            "callsign": callsign,
            "band": band,
            "qth": qth,
            "locator": grid,
            "lat": lat,
            "lon": lon,
            "distance_km": round(distance) if distance is not None else None,
            "sota_ref": sota_ref,
            "comment": comment
        })

    output_data = {
        "date": date,
        "my_callsign": my_callsign,
        "my_locator": my_locator,
        "my_lat": my_lat,
        "my_lon": my_lon,
        "my_sota": my_sota,
        "qsos": qso_list
    }

    output_file = Path(adif_file).parent / "qsos.json"
    with open(output_file, "w") as json_file:
        json.dump(output_data, json_file, indent=4)

    print(f"Conversion complete: {output_file} created")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app.py /path/to/folder")
        sys.exit(1)

    folder_path = Path(sys.argv[1]).resolve()
    if not folder_path.exists() or not folder_path.is_dir():
        print(f"Error: Folder {folder_path} not found or is not a directory.")
        sys.exit(1)

    for adif_file in folder_path.rglob("*.adi"):
        print(f"Processing {adif_file}")
        adif_to_json(adif_file)

    adif_file_path = Path(sys.argv[1]).resolve()
    if not adif_file_path.exists():
        print(f"Error: File {adif_file_path} not found.")
        sys.exit(1)

    adif_to_json(adif_file_path)


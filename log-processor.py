'''
todo

use summitdatabase to look up my lat long for calcing distance
use the formula for distance from s2s
if other end is a summit use lat long from db
missing date time

'''


import adif_io
import json
import math
import sys
from pathlib import Path

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
    my_lat, my_lon = grid_to_latlon(my_locator) if my_locator else (None, None)

    qso_list = []
    for record in records:
        callsign = record.get('CALL')
        band = record.get('BAND')
        qth = record.get('QTH', '')
        grid = record.get('GRIDSQUARE', '')
        sota_ref = record.get('SOTA_REF', '')
        comment = record.get('COMMENT', '')

        if grid:
            lat, lon = grid_to_latlon(grid)
            distance = haversine(my_lat, my_lon, lat, lon) if my_lat and my_lon else None
        else:
            lat, lon, distance = None, None, None

        qso_list.append({
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
        "my_callsign": my_callsign,
        "my_locator": my_locator,
        "my_lat": my_lat,
        "my_lon": my_lon,
        "my_sota": my_sota,
        "qsos": qso_list
    }

    output_file = Path(adif_file).with_suffix(".json")
    with open(output_file, "w") as json_file:
        json.dump(output_data, json_file, indent=4)

    print(f"Conversion complete: {output_file} created")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app.py /path/to/log.adi")
        sys.exit(1)

    adif_file_path = Path(sys.argv[1]).resolve()
    if not adif_file_path.exists():
        print(f"Error: File {adif_file_path} not found.")
        sys.exit(1)

    adif_to_json(adif_file_path)

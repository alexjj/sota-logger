import adif_io
import folium
import os
from geopy.distance import geodesic

def read_adif_log(file_path):
    """ Reads an ADIF log file and returns a list of contacts."""
    with open(file_path, 'r', encoding='utf-8') as f:
        records, _ = adif_io.read_from_string(f.read())
    return records

def generate_markdown(contacts, output_file='contacts.md'):
    """ Generates a markdown table of contacts."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# SOTA Contacts\n\n")
        f.write("| Callsign | Band | QTH | RST | Distance (km) |\n")
        f.write("|----------|------|-----|---------|--------------|\n")

        # my_lat, my_lon = grid_to_latlon(my_grid)

        for contact in contacts:
            callsign = contact.get('CALL', 'Unknown')
            band = contact.get('BAND', 'Unknown')
            qth = contact.get('QTH', 'Unknown')
            comment = contact.get('COMMENT', 'Unknown')
            grid = contact.get('GRIDSQUARE', 'Unknown')
            my_grid = contact.get('MY_GRIDSQUARE', 'Unknown')

            if grid != 'Unknown':
                lat, lon = grid_to_latlon(grid)
                my_lat, my_lon = grid_to_latlon(my_grid)
                distance = str(round(geodesic((my_lat, my_lon), (lat, lon)).km))
            else:
                distance = 'N/A'

            f.write(f"| {callsign} | {band} | {qth} | {comment} | {distance} |\n")

def generate_map(contacts, output_file='contacts_map.html'):
    """ Generates an interactive map of the contacts."""
    m = folium.Map(location=[0, 0], zoom_start=2)

    for contact in contacts:
        callsign = contact.get('CALL', 'Unknown')
        grid = contact.get('GRIDSQUARE', None)

        if grid is not None:
            lat, lon = grid_to_latlon(grid)

            folium.Marker(
                location=[lat, lon],
                popup=f"Callsign: {callsign}\nGrid: {grid}",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)

    m.save(output_file)
    print(f"Map saved as {output_file}")

def grid_to_latlon(maiden):

    maiden = maiden.strip().upper()

    N = len(maiden)
    if not ((8 >= N >= 2) and (N % 2 == 0)):
        raise ValueError("Maidenhead locator requires 2-8 characters, even number of characters")

    Oa = ord("A")
    lon = -180.0
    lat = -90.0

    lon += (ord(maiden[0]) - Oa) * 20
    lat += (ord(maiden[1]) - Oa) * 10

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

if __name__ == "__main__":
    adif_file = 'sota.adi'


    if not os.path.exists(adif_file):
        print(f"Error: {adif_file} not found.")
    else:
        contacts = read_adif_log(adif_file)
        generate_markdown(contacts)
        generate_map(contacts)
        print("Markdown and map generation completed.")

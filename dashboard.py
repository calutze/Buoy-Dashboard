import requests
import urllib.parse
import xml.etree.ElementTree as ET
from tkinter import *
from tkinter import ttk
from tkintermapview import TkinterMapView
import pika
from threading import Thread
import pandas as pd
import matplotlib.pyplot as plot


def location_search():
    address = location_entry.get()
    print(address)
    url = 'https://nominatim.openstreetmap.org/search?q=' + urllib.parse.quote(address) + '&format=json'
    try:
        response = requests.get(url).json()
        result = response[0]["lon"], response[0]["lat"]
        latitude.set(result[1])
        longitude.set(result[0])
        print(result)
        return result
    except Exception as error:
        print(error)
        return None, None


def buoy_search():
    print("Buoy Search")
    # parse active station list
    load_stations()
    parsed_stations = parse_xml('activestations.xml')
    result = []
    latitude_num = float(latitude.get())
    longitude_num = float(longitude.get())
    miles_to_latitude = 69  # Conversion between miles and latitude
    radius_num = float(search_radius.get())/miles_to_latitude
    for station in parsed_stations:
        station_lat = float(station.get('lat'))
        station_lon = float(station.get('lon'))
        if (latitude_num - radius_num) <= station_lat <= (latitude_num + radius_num):
            if (longitude_num - radius_num) <= station_lon <= (longitude_num + radius_num):
                result.append(station)
    # print(result)
    searched_buoys.set(result)
    map.delete_all_marker()
    map.fit_bounding_box((latitude_num + radius_num, longitude_num - radius_num),
                         (latitude_num - radius_num, longitude_num + radius_num))
    location_marker = map.set_position(round(latitude_num,5), round(longitude_num,5), marker=True)
    print(location_marker.position, location_marker.text)
    location_marker.set_text("Search Location")
    markers = []
    for buoy in result:
        markers.append(map.set_marker(float(buoy.get("lat")), float(buoy.get("lon")), text=buoy.get("id"), command=click_buoy_event))


def load_stations():
    station_list_url = "http://www.ndbc.noaa.gov/activestations.xml"
    response = requests.get(station_list_url)
    with open('activestations.xml', 'wb') as f:
        f.write(response.content)


def parse_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    station_list = []
    for child in root:
        station = child.attrib
        station_list.append(station)
    return station_list


def click_buoy_event(marker):
    buoy_id.set(marker.text)
    microservice_thread()


def microservice_thread():
    ms_thread = Thread(target=buoy_request)
    ms_thread.start()


def buoy_request():
    def callback(ch, method, properties, body):
        print(f"{body.decode('utf-8')}")

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='To_Microservice')
    channel.queue_declare(queue='To_Main_Program')
    channel.basic_publish(exchange='', routing_key='To_Microservice', body=buoy_id.get())
    print(f"Sent {buoy_id.get()}")
    channel.basic_consume(queue="To_Main_Program", auto_ack=True, on_message_callback=callback)
    channel.start_consuming()
    connection.close()

class station:
    def __init__(self, filename):
        data = pd.read_csv(filename)

    #def plot_tides(self):

    #def summary_weather_data(self):

def summary_weather():
    x=1

win = Tk()      # Instance of Tkinter frame
win.title("Buoy Data Dashboard")

mainframe = ttk.Frame(win, padding="10")
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
win.columnconfigure(0, weight=1)
win.rowconfigure(0, weight=1)


# Initialize label for location search
location_label = Label(mainframe, text="Location Search")
location_label.grid(column=0, row=1, sticky=(E))
# Create entry area for location search user input
location_entry = StringVar(mainframe)
location_field = Entry(mainframe, width=50, textvariable=location_entry)
location_field.focus_set()
location_field.grid(column=1, row=1, columnspan=2, sticky=(W, E))
# Create Button for location search
ttk.Button(mainframe, text="Search",width=15, command=location_search).grid(column=3, row=1)

# Create Display label for buoy search latitude
latitude_label = Label(mainframe, text="Latitude").grid(column=0, row=2)
latitude = StringVar(mainframe)
latitude_field = Entry(mainframe, textvariable=latitude).grid(column=1, row=2)
# Create Display label for buoy search latitude
longitude_label = Label(mainframe, text="Longitude").grid(column=2, row=2)
longitude = StringVar(mainframe)
longitude_field = Entry(mainframe, textvariable=longitude).grid(column=3, row=2)
# Create Display label for buoy search radius
radius_label = Label(mainframe, text="Radius [miles]").grid(column=4, row=2)
search_radius = StringVar(mainframe)
radius_field = Entry(mainframe, textvariable=search_radius).grid(column=5, row=2)
# Create Button for buoy search
ttk.Button(mainframe, text="Search", width=15, command=buoy_search).grid(column=6, row=2)

# Create Map Widget
map = TkinterMapView(mainframe, width=500, height=500)
map.grid(column=1, row=4, columnspan=5)

# Create Label for buoy id
searched_buoys = Variable()
buoy_label = Label(mainframe, text="Buoy ID:").grid(column=0, row=3)
buoy_id = StringVar(mainframe)
buoy_field = Entry(mainframe, textvariable=buoy_id).grid(column=1, row=3)
# Create Button for buoy data search
ttk.Button(mainframe, text="Get Data", width=15, command=microservice_thread).grid(column=3, row=3)

win.mainloop()

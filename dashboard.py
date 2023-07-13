import requests
import urllib.parse
from geopy.geocoders import Nominatim
import xml.etree.ElementTree as ET
from tkinter import *
from tkinter import ttk

geolocator = Nominatim(user_agent='BuoyDashboard')

def location_search():
    address = location_entry.get()
    print(address)
    url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) + '?format=json'
    try:
        response = requests.get(url).json()
        result = response[0]["lon"], response[0]["lat"]
        latitude.set(result[0])
        longitude.set(result[1])
        print(result)
        return result
    except Exception as e:
        print(e)
        return None, None


def buoy_search():
    print("Buoy Search")
    # parse active station list
    #loadStations()
    parsed_stations = parseXML('activestations.xml')
    result = []
    latitude_num = float(latitude.get())
    longitude_num = float(longitude.get())
    radius_num = float(search_radius.get())
    for station in parsed_stations:
        station_lat = float(station.get('lat'))
        station_lon = float(station.get('lon'))
        if (latitude_num - radius_num) <= station_lat <= (latitude_num + radius_num):
            if (longitude_num - radius_num) <= station_lon <= (longitude_num + radius_num):
                result.append(station)
    #print(result)
    searched_buoys.set(result)
    #thing = searched_buoys.get()



def loadStations():
    station_list_url = "http://www.ndbc.noaa.gov/activestations.xml"
    response = requests.get(station_list_url)
    with open('activestations.xml', 'wb') as f:
        f.write(response.content)


def parseXML(xmlfile):
    tree = ET.parse(xmlfile)
    root = tree.getroot()
    station_list = []
    for child in root:
        station = child.attrib
        station_list.append(station)
    return station_list


#buoy_search()

win = Tk()      # Instance of Tkinter frame
win.title("Buoy Data Dashboard")

mainframe = ttk.Frame(win, padding="10")
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
win.columnconfigure(0, weight=1)
win.rowconfigure(0, weight=1)

#win.geometry("750x500")
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
# Create Display label for location search result
latitude_label = Label(mainframe, text="Latitude").grid(column=0, row=2)
latitude = StringVar(mainframe)
latitude_field = Entry(mainframe, textvariable=latitude).grid(column=1, row=2)
longitude_label = Label(mainframe, text="Longitude").grid(column=2, row=2)
longitude = StringVar(mainframe)
longitude_field = Entry(mainframe, textvariable=longitude).grid(column=3, row=2)
radius_label = Label(mainframe, text="Radius").grid(column=4, row=2)
search_radius = StringVar(mainframe)
radius_field = Entry(mainframe, textvariable=search_radius).grid(column=5, row=2)
ttk.Button(mainframe, text="Search", width=15, command=buoy_search).grid(column=6, row=2)
searched_buoys = Variable()

win.mainloop()




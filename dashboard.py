import requests
import urllib.parse
from geopy.geocoders import Nominatim
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
latitude_label = Label(mainframe, text="Latitude")
latitude_label.grid(column=0, row=2)
latitude = StringVar(mainframe)
latitude_field = Entry(mainframe, textvariable=latitude)
latitude_field.grid(column=1, row=2)
longitude_label = Label(mainframe, text="Longitude")
longitude_label.grid(column=2, row=2)
longitude = StringVar(mainframe)
longitude_field = Entry(mainframe, textvariable=longitude)
longitude_field.grid(column=3, row=2)


win.mainloop()




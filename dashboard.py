import requests
import urllib.parse
import xml.etree.ElementTree as etree
from tkinter import *
from tkinter import ttk
from tkintermapview import TkinterMapView
import pika
from threading import Thread
import pandas as pd
import windrose
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
matplotlib.use('agg')


class Station:
    def __init__(self, file_list):
        self.tide_data = None
        self.weather_data = None
        self.weather_units = None
        self.filtered_wave_data = None
        self.swell_data = None
        for file in file_list:
            if '.dart' in file:
                self._create_tide_data(file)
            if '.txt' in file:
                self._create_weather_data(file)
            if '.spec' in file:
                self._create_swell_data(file)

    def _create_tide_data(self, file):
        self.tide_data = pd.read_csv(file, header=0, delimiter=r"\s+")
        self.tide_data.drop(columns=['T', 'ss'], inplace=True)
        self.tide_data.drop(0, inplace=True)
        self.tide_data['date'] = self.tide_data[['#YY', 'MM', 'DD']].agg('-'.join, axis=1)
        self.tide_data['time'] = self.tide_data[['hh', 'mm']].agg(':'.join, axis=1)
        self.tide_data['datetime'] = self.tide_data['date'] + ' ' + self.tide_data['time']
        self.tide_data['HEIGHT'] = self.tide_data['HEIGHT'].astype(float)

    def _create_weather_data(self, file):
        self.weather_data = pd.read_csv(file, header=0, delimiter=r"\s+", index_col=False)
        self.weather_units = self.weather_data.loc[0].copy(deep=True)
        self.weather_data.drop(0, inplace=True)
        self.filtered_wave_data = self.weather_data[
            (self.weather_data["WVHT"] != 'MM') & (self.weather_data["DPD"] != 'MM') & (
                    self.weather_data["MWD"] != 'MM')]

    def _create_swell_data(self, file):
        x=1

    def air_temperature(self):
        search_air_temp = self.weather_data[self.weather_data["ATMP"] != "MM"]
        if len(search_air_temp) == 0:
            air_temperature = "N/A"
        else:
            air_temperature = search_air_temp['ATMP'].head(1).values[0]
        return air_temperature

    def air_temperature_unit(self):
        return self.weather_units.loc['ATMP']

    def water_temperature(self):
        search_water_temp = self.weather_data[self.weather_data["WTMP"] != 'MM']
        if len(search_water_temp) == 0:
            water_temperature = "N/A"
        else:
            water_temperature = search_water_temp['WTMP'].head(1).values[0]
        return water_temperature

    def water_temperature_unit(self):
        return self.weather_units.loc['WTMP']

    def significant_wave_height(self):
        return self.filtered_wave_data["WVHT"].head(1).values[0]

    def wave_height_unit(self):
        return self.weather_units.loc["WVHT"]

    def swell_period(self):
        return self.filtered_wave_data["DPD"].head(1).values[0]

    def swell_direction(self):
        return self.filtered_wave_data["MWD"].head(1).values[0]

    def wind_speed(self):
        return self.weather_data.loc[1, "WDIR"]

    def wind_speed_unit(self):
        return self.weather_units.loc["WSPD"]

    def wind_direction(self):
        return self.weather_data.loc[1, "WDIR"]

#locationsearchbar
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

#buoysearchbar
def buoy_search():
    print("Buoy Search")
    # parse active station list
    load_stations()
    parsed_stations = parse_xml('activestations.xml')
    result = []
    latitude_num = float(latitude.get())
    longitude_num = float(longitude.get())
    miles_to_latitude = 69  # Conversion between miles and latitude
    radius_num = float(search_radius.get()) / miles_to_latitude
    for station in parsed_stations:
        station_lat = float(station.get('lat'))
        station_lon = float(station.get('lon'))
        if (latitude_num - radius_num) <= station_lat <= (latitude_num + radius_num):
            if (longitude_num - radius_num) <= station_lon <= (longitude_num + radius_num):
                result.append(station)
    mark_buoys(result)

#mapview
def mark_buoys(buoy_list):
    searched_buoys.set(buoy_list)
    miles_to_latitude = 69  # Conversion between miles and latitude
    radius_num = float(search_radius.get()) / miles_to_latitude
    buoy_map.delete_all_marker()
    buoy_map.fit_bounding_box((float(latitude.get()) + radius_num, float(longitude.get()) - radius_num),
                              (float(latitude.get()) - radius_num, float(longitude.get()) + radius_num))
    location_marker = buoy_map.set_position(round(float(latitude.get()), 5),
                                            round(float(longitude.get()), 5), marker=True)
    location_marker.set_text("Search Location")
    markers = []
    for buoy in buoy_list:
        markers.append(buoy_map.set_marker(float(buoy.get("lat")), float(buoy.get("lon")),
                                           text=buoy.get("id"), command=click_buoy_event))

#buoysearchbar
def load_stations():
    station_list_url = "http://www.ndbc.noaa.gov/activestations.xml"
    response = requests.get(station_list_url)
    with open('activestations.xml', 'wb') as f:
        f.write(response.content)

#buoysearchbar
def parse_xml(xml_file):
    tree = etree.parse(xml_file)
    root = tree.getroot()
    station_list = []
    for child in root:
        station = child.attrib
        station_list.append(station)
    return station_list

#mapview
def click_buoy_event(marker):
    buoy_id.set(marker.text)
    microservice_thread()

#buoydatabar
def microservice_thread():
    ms_thread = Thread(target=buoy_request)
    ms_thread.start()

#buoydatabar
def microservice_response(ch, method, properties, body):
    message = body.decode('utf-8')
    if message != 'No files downloaded':
        message_list = message.split(', ')
        print(f"Received Files: {message_list}")
        buoy_data = Station(message_list)
        display_data(buoy_data)

#buoydatabar
def buoy_request():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='To_Microservice')
    channel.queue_declare(queue='To_Main_Program')
    channel.basic_publish(exchange='', routing_key='To_Microservice', body=buoy_id.get())
    print(f"Sent {buoy_id.get()}")
    channel.basic_consume(queue="To_Main_Program", auto_ack=True, on_message_callback=microservice_response)
    channel.start_consuming()
    connection.close()

#resultplots
def tide_plot(station):
    fig = Figure(figsize=(4, 4), dpi=100)
    ax = fig.add_subplot(111)
    station.tide_data.plot(x='datetime', y='HEIGHT', kind='line', legend=None, ax=ax,
                           ylabel='Height [m]', title='Tide', xlim=(0, 200))
    canvas = FigureCanvasTkAgg(fig, master=tide_frame)
    canvas.draw()
    canvas.get_tk_widget().pack()

#resultplots
def summary_weather(station):
    Label(master=weather_frame, justify='right', text="Air").grid(column=0, row=0, sticky=W)
    Label(master=weather_frame, justify='right',
          text=f"{station.air_temperature()} {station.air_temperature_unit()}").grid(column=1, row=0, sticky=W)

    Label(master=weather_frame, justify='right', text="Water").grid(column=0, row=1, sticky=W)
    Label(master=weather_frame, justify='right',
          text=f"{station.water_temperature()} "
               f"{station.water_temperature_unit()}").grid(column=1, row=1, sticky=W)

    Label(master=weather_frame, justify='right', text="Waves").grid(column=0, row=2, sticky=W)
    Label(master=weather_frame, justify='right',
          text=f"{station.significant_wave_height()} {station.wave_height_unit()} @ {station.swell_period()}"
               f" s {station.swell_direction()} \N{DEGREE SIGN}").grid(column=1, row=2, sticky=W)

    Label(master=weather_frame, justify='right', text="Wind").grid(column=0, row=3, sticky=W)
    Label(master=weather_frame, justify='right',
          text=f"{station.wind_speed()} {station.wind_speed_unit()} "
               f"{station.wind_direction()} \N{DEGREE SIGN}").grid(column=1, row=3, sticky=W)

#resultplots
def swell_plot(file_name):
    x = 1

#resultplots
def display_data(station):
    weather_frame.grid_forget()
    tide_frame.grid_forget()
    swell_frame.grid_forget()
    if station.tide_data is not None:
        tide_frame.grid(column=0, row=0)
        tide_plot(station)
    if station.weather_data is not None:
        weather_frame.grid(column=0, row=0)
        summary_weather(station)


win = Tk()  # Instance of Tkinter frame
win.title("Buoy Data Dashboard")

mainframe = ttk.Frame(win, padding="10")
mainframe.grid(column=0, row=0)
weather_frame = ttk.Frame(win, padding='5')
weather_frame.grid(column=0, row=1)
tide_frame = ttk.Frame(win, padding='5')
tide_frame.grid(column=0, row=2)
swell_frame = ttk.Frame(win, padding='5')
swell_frame.grid(column=1, row=2)
win.columnconfigure(0, weight=1)
win.rowconfigure(0, weight=1)

# Initialize label for location search
location_label = Label(mainframe, text="Location Search")
location_label.grid(column=0, row=1, sticky=E)
# Create entry area for location search user input
location_entry = StringVar(mainframe)
location_field = Entry(mainframe, width=50, textvariable=location_entry)
location_field.focus_set()
location_field.grid(column=1, row=1, columnspan=2, sticky=('W', 'E'))
# Create Button for location search
ttk.Button(mainframe, text="Search", width=15, command=location_search).grid(column=3, row=1)

# Create Display label for buoy search latitude
Label(mainframe, text="Latitude").grid(column=0, row=2)
latitude = StringVar(mainframe)
Entry(mainframe, textvariable=latitude).grid(column=1, row=2)
# Create Display label for buoy search latitude
Label(mainframe, text="Longitude").grid(column=2, row=2)
longitude = StringVar(mainframe)
Entry(mainframe, textvariable=longitude).grid(column=3, row=2)
# Create Display label for buoy search radius
Label(mainframe, text="Radius [miles]").grid(column=4, row=2)
search_radius = StringVar(mainframe)
Entry(mainframe, textvariable=search_radius).grid(column=5, row=2)
# Create Button for buoy search
ttk.Button(mainframe, text="Search", width=15, command=buoy_search).grid(column=6, row=2)

# Create Map Widget
buoy_map = TkinterMapView(mainframe, width=500, height=500)
buoy_map.grid(column=1, row=4, columnspan=5)

# Create Label for buoy id
searched_buoys = Variable()
Label(mainframe, text="Buoy ID:").grid(column=0, row=3)
buoy_id = StringVar(mainframe)
Entry(mainframe, textvariable=buoy_id).grid(column=1, row=3)
# Create Button for buoy data search
ttk.Button(mainframe, text="Get Data", width=15, command=microservice_thread).grid(column=3, row=3)

win.mainloop()

import requests
import urllib.parse
import xml.etree.ElementTree as ET
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

class station:
    def __init__(self, filename):
        dart_data = pd.read_csv(filename, header=0, delimiter=r"\s+")

    def tideplotter(self, file_name):
        df = pd.read_csv(file_name, header=0, delimiter=r"\s+")
        df.drop(columns=['T', 'ss'], inplace=True)
        df.drop(0, inplace=True)
        df['date'] = df[['#YY', 'MM', 'DD']].agg('-'.join, axis=1)
        df['time'] = df[['hh', 'mm']].agg(':'.join, axis=1)
        df['datetime'] = df['date'] + ' ' + df['time']
        df['HEIGHT'] = df['HEIGHT'].astype(float)
        df.plot(x='datetime', y='HEIGHT', kind='line', legend=None)
        plt.ylabel('Height [m]')
        plt.title("Tide")
        plt.xlim(0, 500)
        fig = Figure(figsize=(5, 5), dpi=100)
        canvas = FigureCanvasTkAgg(fig, master=figframe)
        canvas.draw()
        canvas.get_tk_widget().pack()
        #plt.show()

    #def summary_weather_data(self):

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
    print(location_marker.position)
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
        message = body.decode('utf-8')
        if message != 'No files downloaded':
            message_list = message.split(', ')
            print(f"Received Files: {message_list}")
            display_data(message_list)

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='To_Microservice')
    channel.queue_declare(queue='To_Main_Program')
    channel.basic_publish(exchange='', routing_key='To_Microservice', body=buoy_id.get())
    print(f"Sent {buoy_id.get()}")
    channel.basic_consume(queue="To_Main_Program", auto_ack=True, on_message_callback=callback)
    channel.start_consuming()
    connection.close()


def tide_plot(file_name):
    tide_data = pd.read_csv(file_name, header=0, delimiter=r"\s+")
    tide_data.drop(columns=['T', 'ss'], inplace=True)
    tide_data.drop(0, inplace=True)
    tide_data['date'] = tide_data[['#YY', 'MM', 'DD']].agg('-'.join, axis=1)
    tide_data['time'] = tide_data[['hh', 'mm']].agg(':'.join, axis=1)
    tide_data['datetime'] = tide_data['date'] + ' ' + tide_data['time']
    tide_data['HEIGHT'] = tide_data['HEIGHT'].astype(float)
    fig = Figure(figsize=(4, 4), dpi=100)
    ax = fig.add_subplot(111)
    tide_data.plot(x='datetime', y='HEIGHT', kind='line', legend=None, ax=ax,
            ylabel='Height [m]', title='Tide', xlim=(0,200))
    canvas = FigureCanvasTkAgg(fig, master=tide_frame)
    canvas.draw()
    canvas.get_tk_widget().pack()
    #toolbar = NavigationToolbar2Tk(canvas, tide_frame)
    #toolbar.update()
    #canvas.get_tk_widget().pack()


def summary_weather(file_name):
    weather_data = pd.read_csv(file_name, header=0, delimiter=r"\s+", index_col=False)
    weather_units = weather_data.loc[0].copy(deep=True)
    weather_data.drop(0, inplace=True)

    search_atmp = weather_data[weather_data["ATMP"] != 'MM']
    if len(search_atmp) == 0:
        air_T = "N/A"
    else:
        air_T = search_atmp['ATMP'].head(1).values[0]
    air_unit = weather_units.loc['ATMP']
    Label(master=weather_frame, justify='right', text="Air").grid(column=0, row=0, sticky=W)
    Label(master=weather_frame, justify='right', text=f"{air_T} {air_unit}").grid(column=1, row=0, sticky=W)

    search_wtmp = weather_data[weather_data["WTMP"] != 'MM']
    if len(search_wtmp) == 0:
        water_T = "N/A"
    else:
        water_T = search_wtmp['WTMP'].head(1).values[0]
    water_unit = weather_units.loc['WTMP']
    Label(master=weather_frame, justify='right', text="Water").grid(column=0, row=1, sticky=W)
    Label(master=weather_frame, justify='right', text=f"{water_T} {water_unit}").grid(column=1, row=1, sticky=W)

    search_sig_wave_height = weather_data[
        (weather_data["WVHT"] != 'MM') & (weather_data["DPD"] != 'MM') & (weather_data["MWD"] != 'MM')]
    sig_wave_height = search_sig_wave_height["WVHT"].head(1).values[0]
    sig_wave_unit = weather_units.loc["WVHT"]
    swell_period = search_sig_wave_height["DPD"].head(1).values[0]
    swell_direction = search_sig_wave_height["MWD"].head(1).values[0]
    Label(master=weather_frame, justify='right', text="Waves").grid(column=0, row=2, sticky=W)
    Label(master=weather_frame, justify='right',
          text=f"{sig_wave_height} {sig_wave_unit} @ {swell_period} s {swell_direction} \N{DEGREE SIGN}").grid(column=1, row=2, sticky=W)

    wind_dir = weather_data.loc[1, 'WDIR']
    wind_speed = weather_data.loc[1, 'WSPD']
    wind_speed_unit = weather_units.loc['WSPD']
    Label(master=weather_frame, justify='right', text="Wind").grid(column=0, row=3, sticky=W)
    Label(master=weather_frame, justify='right',
          text=f"{wind_speed} {wind_speed_unit} {wind_dir} \N{DEGREE SIGN}").grid(column=1, row=3, sticky=W)

def swell_plot(file_name):
    x=1

def display_data(file_list):
    weather_frame.grid_forget()
    tide_frame.grid_forget()
    swell_frame.grid_forget()
    for file in file_list:
        if '.dart' in file:
            tide_frame.grid(column=0, row=2)
            tide_plot(file)
        if '.txt' in file:
            weather_frame.grid(column=0, row=1)
            summary_weather(file)
        if '.data_spec' in file:
            swell_frame.grid(column=1, row=2)
            swell_plot(file)


win = Tk()      # Instance of Tkinter frame
win.title("Buoy Data Dashboard")

mainframe = ttk.Frame(win, padding="10")
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
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

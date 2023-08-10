import requests
import urllib.parse
import xml.etree.ElementTree as et
import tkinter as tk
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
        x = 1

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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Buoy Data Dashboard")
        self.app_data = {"location_entry": tk.StringVar(),
                         "latitude": tk.StringVar(),
                         "longitude": tk.StringVar(),
                         "search_radius": tk.StringVar(),
                         "searched_buoys": tk.StringVar(),
                         "buoy_id": tk.StringVar(),
                         "buoy_data": None}
        self.location_frame = ttk.Frame(self, padding='5')
        self.location_frame.grid(column=0, row=0, sticky='W')
        self.location_search_bar = LocationSearchBar(self.location_frame, self.app_data)
        self.search_bar_frame = ttk.Frame(self, padding='5')
        self.search_bar_frame.grid(column=0, row=1, sticky='W')
        self.buoy_search_bar = BuoySearch(self.search_bar_frame, self.app_data)
        self.plot_frame = ttk.Frame(self, padding='5')
        self.plot_frame.grid(column=1, row=1)


class LocationSearchBar(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__()
        self.controller = controller
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        # Initialize label for location search
        tk.Label(self.parent, text="Location Search").grid(column=0, row=0, sticky="E")
        # Create entry area for location search user input
        location_field = tk.Entry(self.parent, width=50, textvariable=self.controller["location_entry"])
        location_field.grid(column=1, row=0, sticky=("W", "E"))
        location_field.focus_set()
        # Create Button for location search
        ttk.Button(self.parent, text="Search", width=15, command=self.location_search).grid(column=2, row=0)

    def location_search(self):
        address = self.controller["location_entry"].get()
        print(address)
        url = 'https://nominatim.openstreetmap.org/search?q=' + urllib.parse.quote(address) + '&format=json'
        try:
            response = requests.get(url).json()
            result = response[0]["lon"], response[0]["lat"]
            self.controller["latitude"].set(result[1])
            self.controller["longitude"].set(result[0])
            print(result)
            return result
        except Exception as error:
            print(error)
            return None, None


def load_stations():
    station_list_url = "http://www.ndbc.noaa.gov/activestations.xml"
    response = requests.get(station_list_url)
    with open('activestations.xml', 'wb') as f:
        f.write(response.content)


def parse_xml(xml_file):
    tree = et.parse(xml_file)
    root = tree.getroot()
    station_list = []
    for child in root:
        station = child.attrib
        station_list.append(station)
    return station_list


class BuoySearch(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.buoy_map = TkinterMapView(self.parent, width=400, height=400)
        self.create_widgets()

    def create_widgets(self):
        # Create Display label for buoy search latitude
        tk.Label(self.parent, text="Latitude").grid(column=0, row=2)
        tk.Entry(self.parent, textvariable=self.controller['latitude']).grid(column=1, row=2, sticky='W')
        # Create Display label for buoy search latitude
        tk.Label(self.parent, text="Longitude").grid(column=2, row=2)
        tk.Entry(self.parent, textvariable=self.controller['longitude']).grid(column=3, row=2)
        # Create Display label for buoy search radius
        tk.Label(self.parent, text="Radius [miles]").grid(column=4, row=2)
        tk.Entry(self.parent, textvariable=self.controller['search_radius']).grid(column=5, row=2)
        # Create Button for buoy search
        ttk.Button(self.parent, text="Search", width=15, command=self.buoy_search).grid(column=6, row=2)
        # Create Label for buoy id
        tk.Label(self.parent, text="Buoy ID:").grid(column=0, row=3)
        tk.Entry(self.parent, textvariable=self.controller['buoy_id']).grid(column=1, row=3)
        # Create Button for buoy data search
        ttk.Button(self.parent, text="Get Data", width=15,
                   command=self.microservice_thread).grid(column=2, row=3)
        self.buoy_map.grid(column=1, row=4, columnspan=5)

    def buoy_search(self):
        print("Buoy Search")
        load_stations()
        parsed_stations = parse_xml('activestations.xml')
        result = []
        latitude_num = float(self.controller['latitude'].get())
        longitude_num = float(self.controller['longitude'].get())
        miles_to_latitude = 69  # Conversion between miles and latitude
        radius_num = float(self.controller['search_radius'].get()) / miles_to_latitude
        for station in parsed_stations:
            station_lat = float(station.get('lat'))
            station_lon = float(station.get('lon'))
            if (latitude_num - radius_num) <= station_lat <= (latitude_num + radius_num):
                if (longitude_num - radius_num) <= station_lon <= (longitude_num + radius_num):
                    result.append(station)
        self.mark_buoys(result)

    def mark_buoys(self, buoy_list):
        self.controller['searched_buoys'].set(buoy_list)
        miles_to_latitude = 69  # Conversion between miles and latitude
        radius_num = float(self.controller['search_radius'].get()) / miles_to_latitude
        self.buoy_map.delete_all_marker()
        self.buoy_map.fit_bounding_box((float(self.controller['latitude'].get()) + radius_num,
                                        float(self.controller['longitude'].get()) - radius_num),
                                       (float(self.controller['latitude'].get()) - radius_num,
                                        float(self.controller['longitude'].get()) + radius_num))
        location_marker = self.buoy_map.set_position(round(float(self.controller['latitude'].get()), 5),
                                                     round(float(self.controller['longitude'].get()), 5),
                                                     marker=True)
        location_marker.set_text("Search Location")
        markers = []
        for buoy in buoy_list:
            markers.append(self.buoy_map.set_marker(float(buoy.get("lat")), float(buoy.get("lon")),
                                                    text=buoy.get("id"), command=self.click_buoy_event))

    def click_buoy_event(self, marker):
        self.controller['buoy_id'].set(marker.text)
        self.microservice_thread()

    def microservice_thread(self):
        ms_thread = Thread(target=self.buoy_request)
        ms_thread.start()

    def microservice_response(self, ch, method, properties, body):
        message = body.decode('utf-8')
        if message != 'No files downloaded':
            message_list = message.split(', ')
            print(f"Received Files: {message_list}")
            self.controller['buoy_data'] = Station(message_list)
            plots = ResultPlots(self.master.master.plot_frame, self.controller)
            plots.destroy()

    def buoy_request(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='To_Microservice')
        channel.queue_declare(queue='To_Main_Program')
        channel.basic_publish(exchange='', routing_key='To_Microservice',
                              body=self.controller['buoy_id'].get())
        print(f"Sent {self.controller['buoy_id'].get()}")
        channel.basic_consume(queue="To_Main_Program", auto_ack=True,
                              on_message_callback=self.microservice_response)
        channel.start_consuming()
        connection.close()


class ResultPlots(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__()
        self.controller = controller
        self.parent = parent
        self.master.grid_forget()
        self.master.grid(column=1, row=1)
        self.weather_frame = ttk.Frame(self.parent, padding='5')
        self.weather_frame.grid_forget()
        self.weather_frame.grid(column=0, row=0)
        self.tide_frame = ttk.Frame(self.parent, padding='5')
        self.weather_frame.grid_forget()
        self.tide_frame.grid(column=0, row=1)
        self.display_data()

    def display_data(self):
        self.weather_frame.grid_forget()
        self.tide_frame.grid_forget()
        if self.controller['buoy_data'] is not None:
            if self.controller['buoy_data'].weather_data is not None:
                self.weather_frame.grid(column=0, row=0)
                self.summary_weather(self.controller['buoy_data'])
        if self.controller['buoy_data'] is not None:
            if self.controller['buoy_data'].tide_data is not None:
                self.tide_frame.grid(column=0, row=1)
                self.tide_plot(self.controller['buoy_data'])

    def tide_plot(self, station):
        fig = Figure(figsize=(4, 4), dpi=100)
        ax = fig.add_subplot(111)
        station.tide_data.plot(x='datetime', y='HEIGHT', kind='line', legend=None, ax=ax,
                               ylabel='Height [m]', title='Tide', xlim=(0, 150))
        canvas = FigureCanvasTkAgg(fig, master=self.tide_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def summary_weather(self, station):
        tk.Label(master=self.weather_frame, justify='right', text="Air").grid(column=0, row=0, sticky='W')
        tk.Label(master=self.weather_frame, justify='right',
                 text=f"{station.air_temperature()} {station.air_temperature_unit()}").grid(column=1, row=0, sticky='W')

        tk.Label(master=self.weather_frame, justify='right', text="Water").grid(column=0, row=1, sticky='W')
        tk.Label(master=self.weather_frame, justify='right',
                 text=f"{station.water_temperature()} "
                      f"{station.water_temperature_unit()}").grid(column=1, row=1, sticky='W')

        tk.Label(master=self.weather_frame, justify='right', text="Waves").grid(column=0, row=2, sticky='W')
        tk.Label(master=self.weather_frame, justify='right',
                 text=f"{station.significant_wave_height()} {station.wave_height_unit()} @ {station.swell_period()}"
                      f" s {station.swell_direction()} \N{DEGREE SIGN}").grid(column=1, row=2, sticky='W')

        tk.Label(master=self.weather_frame, justify='right', text="Wind").grid(column=0, row=3, sticky='W')
        tk.Label(master=self.weather_frame, justify='right',
                 text=f"{station.wind_speed()} {station.wind_speed_unit()} "
                      f"{station.wind_direction()} \N{DEGREE SIGN}").grid(column=1, row=3, sticky='W')


def main():
    myapp = App()
    myapp.mainloop()


if __name__ == "__main__":
    main()

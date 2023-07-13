import wget as wget
import requests
url = 'https://www.ndbc.noaa.gov/data/realtime2/51002.txt'
#filename = wget.download(url)
#x = requests.get(url)

windy_url = 'https://api.windy.com/api/point-forecast/v2'
myobj = {
    "lat": 19.603,
    "lon": -155.977,
    "model": "gfsWave",
    "parameters": ['waves', 'swell1', 'swell2'],
    "levels": ["surface"],
    "key": 'iS9pnjPWqh9DNrc2RLM53uymWfE2Dgi4'
}
x = requests.post(windy_url, json=myobj)

print(x)
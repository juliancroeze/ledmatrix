from mods.samplebase import SampleBase
from threading import Thread
import threading
import time
import requests
from PIL import Image
from io import BytesIO

class WeatherApp(SampleBase):
    def __init__(self, matrix):
        Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()

    def run(self):
        super(WeatherApp, self).run()

        while self.running:
            weather_data = self.get_weather_data("Amsterdam")
            
            # Fetch weather icon based on condition (cloudy, sunny, etc.)
            weather_condition = weather_data.get('condition', 'clear')
            weather_icon = self.get_weather_icon(weather_condition)
            
            # Display the image for weather
            weather_icon_resized = weather_icon.resize((192, 64))  # Resize image for LED matrix
            self.matrix.SetImage(weather_icon_resized)

            time.sleep(10)  # Refresh every 10 seconds

    def get_weather_data(self, city):
        # Request weather data from wttr.in for the given city
        url = f'http://wttr.in/{city}?format=%C+%t'  # %C = condition, %t = temperature
        
        try:
            response = requests.get(url)
            weather_info = response.text.split()
            if len(weather_info) == 2:
                condition = weather_info[0]
                temperature = weather_info[1]
                return {'condition': condition, 'temperature': temperature}
            else:
                return {'condition': 'clear', 'temperature': 'N/A'}
        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return {'condition': 'clear', 'temperature': 'N/A'}

    def get_weather_icon(self, condition):
        # Map weather conditions to appropriate image URLs
        if condition == "clear":
            return self.get_img_from_url("https://cdn-icons-png.flaticon.com/512/869/869869.png")  # Sunny
        elif condition == "cloudy":
            return self.get_img_from_url("https://cdn-icons-png.flaticon.com/512/869/869874.png")  # Cloudy
        elif condition == "rainy":
            return self.get_img_from_url("https://cdn-icons-png.flaticon.com/512/869/869870.png")  # Rainy
        elif condition == "partly cloudy":
            return self.get_img_from_url("https://cdn-icons-png.flaticon.com/512/869/869879.png")  # Partly Cloudy
        elif condition == "thunderstorm":
            return self.get_img_from_url("https://cdn-icons-png.flaticon.com/512/869/869877.png")  # Thunderstorm
        elif condition == "snow":
            return self.get_img_from_url("https://cdn-icons-png.flaticon.com/512/869/869872.png")  # Snowy
        else:
            return self.get_img_from_url("https://cdn-icons-png.flaticon.com/512/869/869869.png")  # Default icon (Sunny)

    def get_img_from_url(self, url):
        # Fetch image from the URL and convert it to an image object
        try:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            return img
        except Exception as e:
            print(f"Error fetching image from URL: {e}")
            return Image.new("RGB", (192, 64))  # Return a blank image in case of error

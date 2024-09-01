# python-weather-api-backend
A Python application that queries the ClimaTempo Weather API for weather data about specific cities and regions.

A valid ClimaTempo API token is necessary, and one can generate a token via: https://advisor.climatempo.com.br/home/#!/tokens

it is also necessary to apply your city's flag to your token so it has permissions to send requests for weather reports for your city in the API. 

This API backend will cache all weather (1 hour expiration time) and city identification info (cached indefinitely) in its memory cache, so repetated requests for the same resources won't end up consuming the API unecessarily.

Also, it has robust logging support (example):

```2024-08-31 01:48:11,801 - __main__ - INFO - Incoming search for city ID request for city name: Florianópolis and state: SC```  
```2024-08-31 01:48:11,802 - __main__ - INFO - Cache hit for City: Florianópolis```  
```2024-08-31 01:48:11,802 - __main__ - INFO - Finished search for city ID for city name: Florianópolis and state: SC```  
```2024-08-31 01:48:11,803 - werkzeug - INFO - 127.0.0.1 - - [31/Aug/2024 01:48:11] "POST /weather/getCityId HTTP/1.1" 200 -```  

A detailed Postman Collection is also provided in the package for easier learning of its usage.

The main endpoints are:

-POST /weather/getInfo: Will query the ClimaTempo API, using the provided City ID and number of future days to be included in the weather report.  
-POST /weather/getCityId: Get specific city's ID by city name and state name abbreviation. This is an utility endpoint to facilitate the search of city IDs to request weather reports.  
-PUT /weather/registerCity: Register city flag for token, so token has access to the weather report for the chosen city  

## Technologies used:
-Python  
-Flask (For creating the API endpoints)  
-Flask-Restful  
-Flask-CORS  
-Python HTTP Requests  
-Python Logging  
-Memory Caching (Caches the weather reports for avoidance of unecessary API calls for the same weather report info)  

Flask install:
```pip3 install Flask```

Flask-Cors install:
```pip3 install -U flask-cors```

Flask-Restful install:
```pip3 install flask-restful```

HTTP Requests install:
```pip3 install requests```

Run application (Linux):
```python3 weather_api_backend.py```

Run application (Windows):
```python weather_api_backend.py```

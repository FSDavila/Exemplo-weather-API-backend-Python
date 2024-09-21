from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from urllib.parse import urlencode
import time
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

# Create a logger object
logger = logging.getLogger(__name__)

# Base URL for the weather API
BASE_URL_API = 'http://apiadvisor.climatempo.com.br/api/v1/forecast/locale/'
CITY_API_BASE_URL = 'http://apiadvisor.climatempo.com.br/api/v1/locale/city'

# Initialize an empty cache dictionary
weatherInfoCache = {}
cityInfoCache = {}
WEATHER_CACHE_EXPIRATION_TIME = 3600  # Cache expiration time for weather information by city in seconds (1 hour)

@app.route('/weather/getInfo', methods=['POST'])
def get_info():
    try:
        # Read the form data from the frontend request
        data = request.form
        headers = request.headers

        # Retrieve city ID and forecast days from the form data
        city_id = data.get("city_id", "")
        forecast_days = data.get("forecast_days", "15")

        logger.info("Incoming request for weather report for city ID: " + city_id + " for the next " + forecast_days + " days")

        # Retrieve the API token from the request headers
        token_api = headers.get('token')

        if not city_id:
            logger.error('Missing required parameter "city_id"')
            return jsonify({'error': 'Missing required parameter "city_id"'}), 400
        
        if not token_api:
            logger.error('Missing API Access Token (header "token")')
            return jsonify({'error': 'Missing API Access Token (header "token")'}), 400

        # Check cache first
        cached_data = get_cached_weather_data(city_id, forecast_days)
        if cached_data:
            logger.info("Finished processing weather report for city ID: " + city_id + " for the next " + forecast_days + " days")
            return jsonify(cached_data)

        # Construct the URL with query parameters
        url = f"{BASE_URL_API}{city_id}/days/{forecast_days}?token={token_api}"

        # Make the GET request to the API
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Log response content
        logger.info('API Response Status Code: %d', response.status_code)
        logger.info('API Response JSON: %s', response.json())

        # Store response data in cache
        store_weather_data(city_id, forecast_days, response.json())
        
        logger.info("Finished processing weather report for city ID: " + city_id + " for the next " + forecast_days + " days")

        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        logger.error('Request error: %s', e)
        response_json = response.json()
        error_detail = response_json.get("detail", "Request error")
        logger.error('API Response JSON: %s', response_json)
        return jsonify({'error': error_detail, 'details': str(e)}), response.status_code
    except Exception as e:
        logger.error('Unexpected error: %s', e)
        return jsonify({'error': 'Unexpected error', 'details': str(e)}), 500
    
@app.route('/weather/v2/getInfo', methods=['POST'])
def get_info_v2():
    try:
        # Read the form data from the frontend request
        data = request.form
        headers = request.headers

        # Retrieve city ID, city name, state, and forecast days from the form data
        city_id = data.get("city_id", "")
        city_name = data.get("city_name", "")
        state = data.get("state", "")
        forecast_days = data.get("forecast_days", "15")

        # Determine the city identifier for logging
        if city_name:
            city_identifier = city_name
        elif city_id:
            city_identifier = f"ID: {city_id}"
        else:
            city_identifier = "Not provided"

        logger.info("Incoming request for weather report for city %s for the next %s days", city_identifier, forecast_days)

        # Retrieve the API token from the request headers
        token_api = headers.get('token')

        if not token_api:
            logger.error('Missing API Access Token (header "token")')
            return jsonify({'error': 'Missing API Access Token (header "token")'}), 400

        if city_id:
            # If city ID is provided, use it directly
            city_id = city_id
        elif city_name and state:
            # If city name and state are provided, fetch city ID from the API
            city_id = get_city_id_from_api_internal(city_name, state, token_api)
            if not city_id:
                logger.error('Could not find city ID for city name: %s and state: %s', city_name, state)
                return jsonify({'error': 'City not found'}), 404
        else:
            logger.error('Missing required parameters "city_id" or both "city_name" and "state"')
            return jsonify({'error': 'Missing required parameters'}), 400

        # Check cache first
        cached_data = get_cached_weather_data(city_id, forecast_days)
        if cached_data:
            logger.info("Finished processing weather report for city ID: " + str(city_id) + " for the next " + forecast_days + " days")
            return jsonify(cached_data)

        # Construct the URL with query parameters
        url = f"{BASE_URL_API}{city_id}/days/{forecast_days}?token={token_api}"

        # Make the GET request to the API
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Log response content
        logger.info('API Response Status Code: %d', response.status_code)
        logger.info('API Response JSON: %s', response.json())

        # Store response data in cache
        store_weather_data(city_id, forecast_days, response.json())
        
        logger.info("Finished processing weather report for city ID: " + str(city_id) + " for the next " + forecast_days + " days")

        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        logger.error('Request error: %s', e)
        response_json = response.json()
        error_detail = response_json.get("detail", "Request error")
        logger.error('API Response JSON: %s', response_json)
        return jsonify({'error': error_detail, 'details': str(e)}), response.status_code
    except Exception as e:
        logger.error('Unexpected error: %s', e, exc_info=True)
        return jsonify({'error': 'Unexpected error', 'details': str(e)}), 500    

@app.route('/weather/registerCity', methods=['PUT'])
def register_city():
    try:
        # Read the form data from the frontend request
        data = request.form
        headers = request.headers 

        logger.info("Incoming request for city ID token registration")
        # Retrieve the API token from the request headers
        token_api = headers.get('token')
        if not token_api:
            logger.error('Missing API Access Token (header "token")')
            return jsonify({'error': 'Missing API Access Token (header "token")'}), 400

        # Define the URL for registering cities
        BASE_URL_REGISTER_CITY = f'http://apiadvisor.climatempo.com.br/api-manager/user-token/{token_api}/locales'

        # Retrieve and format the locale IDs from the form data
        locale_ids = data.getlist("city_id")  # Use getlist to retrieve a list of values
        if not locale_ids:
            logger.error('No locale IDs provided for registration in API token')
            return jsonify({'error': 'No locale IDs provided for registration in API token'}), 400

        # Ensure all are integers
        locale_ids = [int(id) for id in locale_ids if id.isdigit()]  
        if not locale_ids:
            logger.error('Invalid locale IDs provided')
            return jsonify({'error': 'Invalid locale IDs provided'}), 400

        # Prepare the data for the PUT request
        encoded_data = urlencode({'localeId[]': locale_ids}, doseq=True)
        
        # Headers
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Make the PUT request
        response = requests.put(BASE_URL_REGISTER_CITY, headers=headers, data=encoded_data)
        response.raise_for_status()  # Raise HTTPError for bad responses
        logger.info("Finished request for city ID token registration")
        
        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        logger.error('Request error: %s', e)
        response_json = response.json()
        error_detail = response_json.get("detail", "Request error")
        logger.error('API Response JSON: %s', response_json)
        return jsonify({'error': error_detail, 'details': str(e)}), response.status_code
    except Exception as e:
        logger.error('Unexpected error: %s', e)
        response_json = response.json()
        error_detail = response_json.get("detail", "Unknown error")
        logger.error('API Response JSON: %s', response_json)
        return jsonify({'error': 'Unexpected error', 'details': str(e)}), 500

@app.route('/weather/getCityId', methods=['POST'])
def get_city_id():
    try:
        # Read the form data from the frontend request
        data = request.form
        headers = request.headers

        # Retrieve city name, state, and API token from the form data and headers
        city_name = data.get("city_name", "")
        state = data.get("state", "")
        token_api = headers.get('token')

        logger.info("Incoming search for city ID request for city name: " + city_name + " and state: " + state)
    
        if not city_name:
            logger.error('Missing required parameter "city_name"')
            return jsonify({'error': 'Missing required parameter "city_name"'}), 400
        
        #if not state:
        #    logger.error('Missing required parameter "state"')
        #    return jsonify({'error': 'Missing required parameter "state"'}), 400
        
        if not token_api:
            logger.error('Missing API Access Token (header "token")')
            return jsonify({'error': 'Missing API Access Token (header "token")'}), 400

        # Check cache first
        cached_data = get_cached_city_data(city_name, state)
        if cached_data:
            logger.info("Finished search for city ID for city name: " + city_name + " and state: " + state)
            return jsonify(cached_data)

        # Construct the URL with query parameters
        params = {
            'name': city_name,
            'state': state,
            'token': token_api
        }
        url = f"{CITY_API_BASE_URL}?{urlencode(params)}"

        # Make the GET request to the API
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Log response content for debugging
        logger.info('API Response Status Code: %d', response.status_code)
        logger.info('API Response JSON: %s', response.json())
        
        store_city_data(city_name, state, response.json())
        
        logger.info("Finished search for city ID for city name: " + city_name + " and state: " + state)

        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        logger.error('Request error: %s', e)
        response_json = response.json()
        error_detail = response_json.get("detail", "Request error")
        logger.error('API Response JSON: %s', response_json)
        return jsonify({'error': error_detail, 'details': str(e)}), response.status_code
    except Exception as e:
        logger.error('Unexpected error: %s', e)
        response_json = response.json()
        error_detail = response_json.get("detail", "Unknown error")
        logger.error('API Response JSON: %s', response_json)
        return jsonify({'error': 'Unexpected error', 'details': str(e)}), 500

def store_weather_data(city_id, forecast_days, weather_data):
    """Store weather data in the cache."""
    if not weather_data:
        logger.info('No data to cache for the period %s days for City ID: %s', forecast_days, city_id)
        return 
    cache_key = (city_id, forecast_days)
    weatherInfoCache[cache_key] = {
        'data': weather_data,
        'timestamp': time.time()
    }
    logger.info('Cached data for the period %s days for City ID: %s', forecast_days, city_id)

def get_cached_weather_data(city_id, forecast_days):
    """Retrieve weather data from the cache if it's still valid."""
    cache_key = (city_id, forecast_days)
    if cache_key in weatherInfoCache:
        cached_data = weatherInfoCache[cache_key]
        if time.time() - cached_data['timestamp'] < WEATHER_CACHE_EXPIRATION_TIME:
            logger.info('Cache hit for the period %s days for City ID: %s', forecast_days, city_id)
            return cached_data['data']
        else:
            del weatherInfoCache[cache_key]  # Remove expired cache
    logger.info('Cache miss for the period %s days for City ID: %s', forecast_days, city_id)
    return None

def store_city_data(city_name, state, city_data):
    """Store city data in the cache."""
    if not city_data:
        logger.info('No data to cache for for City name: %s', city_name)
        return 
    cache_key = (city_name, state)
    cityInfoCache[cache_key] = {
        'data': city_data,
        'timestamp': time.time()
    }
    logger.info('Cached data for the city: %s', city_name)
    
def get_cached_city_data(city_name, state):
    """Retrieve city data from the cache if it's still valid."""
    cache_key = (city_name, state)
    if cache_key in cityInfoCache:
        cached_data = cityInfoCache[cache_key]
        logger.info('Cache hit for City: %s', city_name)
        return cached_data['data']
    logger.info('Cache miss for City: %s', city_name)
    return None    

def get_city_id_from_api_internal(city_name, state, token_api):
    """Retrieve the city ID based on the city name and state from the API."""
    params = {
        'name': city_name,
        'state': state,
        'token': token_api
    }
    url = f"{CITY_API_BASE_URL}?{urlencode(params)}"
    try:
        logger.info('Getting city ID for weather report request: %s', city_name)
        response = requests.get(url)
        response.raise_for_status()
        city_data = response.json()
        if city_data:
            # Assume the first result is the correct city
            return city_data[0].get("id")
        else:
            return None
    except requests.exceptions.RequestException as e:
        logger.error('Failed to fetch city ID from API: %s', e)
        return None

# Remember to configure the host and port if going to open the API to the internet
#if __name__ == '__main__':
    #app.run(host="localhost", port=8080, debug=False)
    #app.run(debug=False)

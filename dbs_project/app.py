from flask import Flask, request, jsonify, render_template
import requests
import mysql.connector

app = Flask(__name__)  # ✅ Define the Flask app

API_KEY = "a9b49f91afa3434d90a93038251903"  # Replace with your actual API key

def get_db_connection():
    """Creates a new MySQL connection."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="database123",  # Replace with your MySQL password
        database="weather_db"
    )
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_weather', methods=['GET'])
def get_weather():
    """Fetch weather details for a city and update the search count."""
    city = request.args.get('city')
    if not city:
        return render_template('get_weather.html', weather_data=None)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM WeatherSearch WHERE city = %s", (city,))
    existing_weather = cursor.fetchone()

    if existing_weather:
        cursor.execute("UPDATE WeatherSearch SET search_count = search_count + 1 WHERE city = %s", (city,))
        db.commit()
        cursor.close()
        db.close()
        return render_template('get_weather.html', weather_data=existing_weather)

    # Fetch fresh data from API
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        weather_data = {
            "city": city,
            "temperature": data.get("current", {}).get("temp_c"),
            "humidity": data.get("current", {}).get("humidity"),
            "condition_text": data.get("current", {}).get("condition", {}).get("text", "Unknown"),
        }

        # Insert or update the city in the database
        query = """INSERT INTO WeatherSearch (city, temperature, humidity, condition_text, search_count, last_updated) 
                   VALUES (%s, %s, %s, %s, 1, CURRENT_TIMESTAMP) 
                   ON DUPLICATE KEY UPDATE 
                   temperature = VALUES(temperature), 
                   humidity = VALUES(humidity), 
                   condition_text = VALUES(condition_text), 
                   search_count = search_count + 1, 
                   last_updated = CURRENT_TIMESTAMP"""
        values = (city, weather_data["temperature"], weather_data["humidity"], weather_data["condition_text"])
        cursor.execute(query, values)
        db.commit()

        cursor.close()
        db.close()

        return render_template('get_weather.html', weather_data=weather_data)
    else:
        cursor.close()
        db.close()
        return render_template('get_weather.html', weather_data=None, error="City not found.")
    
    
@app.route('/get_cities_by_temp', methods=['GET'])
def get_cities_by_temp():
    month = request.args.get('month')              # e.g. "Jan"
    min_temp = request.args.get('min_temp', type=float)
    max_temp = request.args.get('max_temp', type=float)
    continent = request.args.get('continent')      # e.g. "Europe"
    good_aqi = request.args.get('good_aqi')        # "on" if checked

    # ✅ Render the search form if no valid query params are provided
    if not (month and min_temp is not None and max_temp is not None):
        return render_template('search.html')

    matching_cities = []

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = f"""
        SELECT city, country, `{month}` AS temp, continent, AQI
        FROM city_temperatures
        WHERE `{month}` BETWEEN %s AND %s
    """
    params = [min_temp, max_temp]

    if continent:
        query += " AND continent = %s"
        params.append(continent)

    if good_aqi == "on":
        query += " AND AQI < 50"

    cursor.execute(query, tuple(params))
    results = cursor.fetchall()

    for row in results:
        matching_cities.append({
            'city': row['city'],
            'country': row['country'],
            'avg_temp': row['temp'],
            'continent': row['continent'],
            'aqi': row['AQI']
        })

    cursor.close()
    db.close()

    return render_template(
        'city_results.html',
        cities=matching_cities,
        month=month,
        min_temp=min_temp,
        max_temp=max_temp,
        continent=continent,
        good_aqi=good_aqi
    )

if __name__ == '__main__':
    app.run(debug=False)
    
    
    
'''
def get_travel_cities():
    """Fetch city names from the database."""
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("SELECT city_name FROM Cities")
    cities = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    db.close()
    
    return cities

def save_weather_bulk():
    saved_cities = []
    failed_cities = []
    
    travel_cities = get_travel_cities()  # Fetch cities from DB
    db = get_db_connection()
    cursor = db.cursor()

    for city in travel_cities:
        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            try:
                temperature = data["current"]["temp_c"]
                humidity = data["current"]["humidity"]
                condition = data["current"]["condition"]["text"]

                query = """INSERT INTO Weather (location, temperature_avg, humidity, weather_type)
                           VALUES (%s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE 
                           temperature_avg = VALUES(temperature_avg), 
                           humidity = VALUES(humidity), 
                           weather_type = VALUES(weather_type)"""
                values = (city, temperature, humidity, condition)

                cursor.execute(query, values)
                db.commit()
                saved_cities.append(city)
            except KeyError as e:
                failed_cities.append(city)
        else:
            failed_cities.append(city)

    cursor.close()
    db.close()
    return saved_cities, failed_cities  # ✅ Return lists instead of JSON response

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/search_weather')
def search_weather():
    saved_cities, failed_cities = save_weather_bulk()  # ✅ Fetch weather & store in DB
    return render_template("search_weather.html", saved_cities=saved_cities, failed_cities=failed_cities)

@app.route('/get_cities_by_weather', methods=['GET'])
def get_cities_by_weather():
    user_weather = request.args.get('weather', '').lower()
    matching_cities = []

    if user_weather:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("SELECT location FROM Weather WHERE weather_type LIKE %s", (f"%{user_weather}%",))
        matching_cities = [row[0] for row in cursor.fetchall()]

        cursor.close()
        db.close()

    return render_template('search_weather.html', weather=user_weather, matching_cities=matching_cities)
'''
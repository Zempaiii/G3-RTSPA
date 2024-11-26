from flask import request, jsonify, Flask, render_template
import os, alpha_vantage, sqlite3, requests
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY1 = os.getenv('ALPHA_VANTAGE_API_KEY1')
API_KEY2 = os.getenv('ALPHA_VANTAGE_API_KEY2')
API_KEY3 = os.getenv('ALPHA_VANTAGE_API_KEY3')
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')

app = Flask(__name__)

def search_stocks(query):
    api_key = [API_KEY1, API_KEY2, API_KEY3]
    for key in api_key:
        url = f'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={key}'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("bestMatches", []) == []:
                continue
            else:
                return data.get("bestMatches", [])
    

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    matches = search_stocks(query)
    
    if not matches:
        return jsonify({"error": "API request failed"}), 500
    elif matches == "limit_exceeded":
        return jsonify({"error": "API limit exceeded"}), 429
    else:
        suggestions = [
            {
                "symbol": match.get("1. symbol"),
                "name": match.get("2. name"),
                "region": match.get("4. region"),
                "currency": match.get("8. currency")
            }
            for match in matches
        ]
    if not suggestions:
        return jsonify({"error": "API request failed"}), 500

    return jsonify(suggestions)


@app.route('/home')
def preview():
    return render_template('index.html')

@app.route('/add')
def add_stocks():
    return render_template('adds.html')

@app.route('/remove')
def remove_stocks():
    return render_template('removes.html')

@app.route('/spiaa?symbol=<symbol>')
def spiaa():
    symbol = request.args.get('symbol', '')
    name = request.args.get('name', '')
    region = request.args.get('region', '')
    currency = request.args.get('currency', '')
    
    url = f'https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/2023-01-09/2023-02-10?adjusted=true&sort=asc&apiKey={POLYGON_API_KEY}'
    response = requests.get(url)
    data = response.json()
    
    if response.status_code != 200 or 'results' not in data:
        return jsonify({"error": "Failed to fetch data from Polygon API"}), 500
    
    return render_template('spiaa.html', stock_name=name, symbol=symbol, region=region, currency=currency, chart_data=json.dumps(data['results']))

if __name__ == '__main__':
    app.run(debug=True)
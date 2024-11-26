from flask import request, jsonify, Flask, render_template
import os, alpha_vantage, sqlite3, requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

app = Flask(__name__)

def search_stocks(query):
    url = f'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "Note" in data and "API call frequency" in data["Note"]:
            return "limit_exceeded"
        return data.get("bestMatches", [])
    return ["huh"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    matches = search_stocks(query)
    
    if matches == ["huh"]:
        return jsonify({"error": "API request failed"}), 500
    elif matches == "limit_exceeded":
        return jsonify({"error": "API limit exceeded"}), 429

    suggestions = [
        {
            "symbol": match.get("1. symbol"),
            "name": match.get("2. name"),
            "region": match.get("4. region"),
            "currency": match.get("8. currency")
        }
        for match in matches
    ]

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

if __name__ == '__main__':
    app.run(debug=True)
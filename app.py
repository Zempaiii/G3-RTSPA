from flask import request, jsonify, Flask, render_template
import os, alpha_vantage, sqlite3, requests, plotly, time
from datetime import datetime, timedelta
import plotly.graph_objects as go
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY = os.getenv('API_KEY')

app = Flask(__name__)

def search_stocks(query):
    url = f'https://ticker-2e1ica8b9.now.sh//keyword/{query}'
    response = requests.get(url)
    data = response.json()
    return data

def fetch_polygon_data(symbol):
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    url = f'https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&apiKey=_zh5HNxfNX9YSJ706qr5p_OoRDWwn0RC'
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error fetching data: {response.text}")
        return None
    return response.json()

def prepare_candle_plot(data, symbol):
    results = data.get("results", [])
    dates = [entry["t"] for entry in results]
    open_prices = [entry["o"] for entry in results]
    high_prices = [entry["h"] for entry in results]
    low_prices = [entry["l"] for entry in results]
    close_prices = [entry["c"] for entry in results]

    dates = [datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d') for ts in dates]

    fig = go.Figure(data=[go.Candlestick(
        x=dates,
        open=open_prices,
        high=high_prices,
        low=low_prices,
        close=close_prices,
        hoverinfo="x+open+high+low+close",
    )])

    fig.update_layout(
        title=f"Candlestick Chart for {symbol.upper()}",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=True,
        template="plotly_white"
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@app.route('/')
def home():
    symbol_data = [
        {"symbol": "MSFT", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
        {"symbol": "AMZN", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
        {"symbol": "WMT", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
    ]
    
    for data in symbol_data:
        url = f'https://api.polygon.io/v1/open-close/{data["symbol"]}/{(datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d')}?adjusted=true&apiKey=_zh5HNxfNX9YSJ706qr5p_OoRDWwn0RC'
        response = requests.get(url)
        if response.status_code != 200:
            time.sleep(60)
            response = requests.get(url)
        results = response.json()
        data["price"] = f"{results['close']:.2f}"
        data["percent"] = f"{((results["close"] - results["open"]) / results["open"] * 100):.2f}"
        data["high"] = f"{results["high"]:.2f}"
        data["low"] = f"{results["low"]:.2f}"
        data["volume"] = f"{(results["volume"] / 1000000):.2f}"
            
    return render_template('index.html', 
                           price_1 = symbol_data[0]["price"], price_2 = symbol_data[1]["price"], price_3 = symbol_data[2]["price"],
                           percent_1 = symbol_data[0]["percent"], percent_2 = symbol_data[1]["percent"], percent_3 = symbol_data[2]["percent"], 
                           high_1 = symbol_data[0]["high"], high_2 = symbol_data[1]["high"], high_3 = symbol_data[2]["high"], 
                           low_1 = symbol_data[0]["low"], low_2 = symbol_data[1]["low"], low_3 = symbol_data[2]["low"], 
                           vol_1 = symbol_data[0]["volume"], vol_2 = symbol_data[1]["volume"], vol_3 = symbol_data[2]["volume"])
    
@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    matches = search_stocks(query)
    suggestions = [
        {
            "symbol": match.get("symbol"),
            "name": match.get("name")
        }
        for match in matches
    ]

    return jsonify(suggestions)

@app.route('/home')
def preview():
    return home()

@app.route('/add')
def add_stocks():
    return render_template('adds.html')

@app.route('/remove')
def remove_stocks():
    return render_template('removes.html')
@app.route('/spiaa')
def spiaa():
    symbol = request.args.get('symbol', '').strip()
    name = request.args.get('name', '').strip()
    
    data = fetch_polygon_data(symbol)
    
    if data is None or 'results' not in data:
        return jsonify({"error": "Failed to fetch data from Polygon API"}), 500
    
    return render_template('spiaa.html', name=name, symbol=symbol, chart_data=json.dumps(data['results']))

if __name__ == '__main__':
    app.run(debug=True)
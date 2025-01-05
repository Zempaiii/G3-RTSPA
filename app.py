from flask import request, jsonify, Flask, render_template, session
import os, sqlite3, requests, plotly, random
from datetime import datetime
import plotly.graph_objects as go
from dotenv import load_dotenv
import json

load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Add a secret key for session management

# search suggestion logic
def search_stocks(query):
    conn = sqlite3.connect('tickers.db')
    cursor = conn.cursor()
    
    command = """
            SELECT Symbol, Name FROM tickers
            WHERE symbol LIKE ? OR Name LIKE ?
            LIMIT 15
            """
    cursor.execute(command, (f'%{query}%', f'%{query}%'))
    
    results = cursor.fetchall()
    conn.close()
    
    results_dict = [{'Symbol': symbol, 'Name': name} for symbol, name in results]
    return results_dict

# api fetching logic
def fetch_api_data(symbol):
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?timeframe=5min&limit=1000&adjustment=raw&feed=sip&sort=asc"
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": "PK9XXY01BXT1F6L9EFZ4",
        "APCA-API-SECRET-KEY": "vdlBS5PgF4Lp7SgyYm42MCF5jm8JUlpPMEGvLnT3"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching data: {response.text}")
        return None
    return response.json()

def prepare_candle_plot(data, symbol):
    print(data)
    results = data.get(symbol, [])
    dates = [entry["t"] for entry in results]
    dates = [datetime.fromtimestamp(ts / 1000) for ts in dates]
    open_prices = [entry["o"] for entry in results]
    high_prices = [entry["h"] for entry in results]
    low_prices = [entry["l"] for entry in results]
    close_prices = [entry["c"] for entry in results]

    dates = [datetime.fromtimestamp(ts / 1000).astimezone().strftime('%x %X') for ts in dates]  # Use system's timezone

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

# homepage backend
@app.route('/')
def home():
    
    symbol_data = [
        {"symbol": "", "name": "", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
        {"symbol": "", "name": "", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
        {"symbol": "", "name": "", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
    ]
    
    for data in symbol_data:
        
        url = f"https://data.alpaca.markets/v1beta1/screener/stocks/movers?top=10"
        movers = ["gainers", "losers"]
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": "PK9XXY01BXT1F6L9EFZ4",
            "APCA-API-SECRET-KEY": "vdlBS5PgF4Lp7SgyYm42MCF5jm8JUlpPMEGvLnT3"
        }
        
        screen = movers[random.randint(0, 1)] # choose between gainers or losers
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching data: {response.text}")
            break
        
        results = response.json().get(screen, [])
        selected_result = results[random.randint(0, 9)]
        data["symbol"] = selected_result["symbol"]
        print(data['symbol'])
        data["name"] = search_stocks(data["symbol"])[0].get("Name")
        data["price"] = f"{selected_result['price']:.2f}"
        data["percent"] = f"{selected_result['percent_change']:.2f}"
        
        url = f"https://data.alpaca.markets/v2/stocks/{data['symbol']}/bars/latest?feed=iex"
        response = requests.get(url, headers=headers)
        latest_bar = response.json().get("bar", {})
        data["high"] = f"{latest_bar['h']:.2f}"
        data["low"] = f"{latest_bar['l']:.2f}"
        data["volume"] = f"{(latest_bar['v'] / 1000):.2f}"
            
    return render_template('index.html', stocks=symbol_data)

# search suggestion backend    
@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    matches = search_stocks(query)

    return jsonify(matches)

# to be removed
@app.route('/add')
def add_stocks():
    return render_template('adds.html')

# to be removed
@app.route('/remove')
def remove_stocks():
    return render_template('removes.html')

# retrieving graph data from API
@app.route('/spiaa')
def spiaa():
    symbol = session.get('symbol', '').strip()
    name = session.get('name', '').strip()
    
    data = fetch_api_data(symbol)
    if data is None or 'bars' not in data:
        return jsonify({"error": "Failed to fetch data from API"}), 500
    
    chart_data = prepare_candle_plot(data, symbol)
    
    return render_template('spiaa.html', name=name, symbol=symbol, chart_data=chart_data)

@app.route('/set_stock') 
def set_stock():
    symbol = request.args.get('symbol', '').strip()
    name = request.args.get('name', '').strip()
    session['symbol'] = symbol
    session['name'] = name
    print(session)
    return jsonify({"message": "Stock set in session"}), 200

if __name__ == '__main__':
    app.run(debug=True)
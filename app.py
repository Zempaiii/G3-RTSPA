from flask import request, jsonify, Flask, render_template, session, redirect, url_for, flash
import os, sqlite3, requests, plotly, random
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from werkzeug.security import check_password_hash, generate_password_hash
import re
import plotly.graph_objects as go
from dotenv import load_dotenv
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)

def check_login():
    if 'username' not in session:
        return login()
    return None

def send_verification_email(email,code):
    load_dotenv()
    mail_server = os.getenv('MAIL_SERVER')
    mail_port = os.getenv('MAIL_PORT')
    mail_username = os.getenv('MAIL_USERNAME')
    mail_password = os.getenv('MAIL_PASSWORD')

    msg = MIMEText(f'Your verification code is: {code}')
    msg['Subject'] = 'SwiftStock Verification Code'
    msg['From'] = mail_username
    msg['To'] = email

    with smtplib.SMTP(mail_server, mail_port) as server:
        server.starttls()
        server.login(mail_username, mail_password)
        server.sendmail(mail_username, email, msg.as_string())

def calculate_sma(prices, period):
    if len(prices) < period:
        return None  # Not enough data to calculate SMA
    sma = []
    for i in range(len(prices) - period + 1):
        sma.append(sum(prices[i:i + period]) / period)
    return sma

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
    results_dict.sort(key=lambda x: (query.lower() not in x['Symbol'].lower(), query.lower() not in x['Name'].lower()))
    return results_dict

# api fetching logic
def fetch_api_data(symbol, timeframe):
    day = {'1W': [7, '5T'], '1M': [30, '1H'], '1Y': [365, '1D'], '5Y': [1825, '1W']}
    day = day.get(timeframe)
    end = datetime.now().strftime('%Y-%m-%dT00:00:00Z')
    start = (datetime.now() - timedelta(days=day[0])).strftime('%Y-%m-%dT00:00:00Z')
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?timeframe={day[1]}&start={start}&end={end}&limit=1000&adjustment=raw&feed=iex&sort=asc"
    print(day)
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

def prepare_candle_plot(data, sma=None, ema=None, macd=None, rsi=None, bollinger=None, volume=None):
    results = data.get('bars', [])
    dates = [entry["t"] for entry in results]
    dates = [datetime.strptime(entry["t"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8) for entry in results]
    open_prices = [entry["o"] for entry in results]
    high_prices = [entry["h"] for entry in results]
    low_prices = [entry["l"] for entry in results]
    close_prices = [entry["c"] for entry in results]

    fig = go.Figure(data=[go.Candlestick(
        x=dates,
        open=open_prices,
        high=high_prices,
        low=low_prices,
        close=close_prices
    )])
    
    if sma:
        fig.add_trace(go.Scatter(
            x=dates,
            y=sma,
            mode='lines',
            name='SMA',
            line=dict(color='blue', width=2)
        ))


    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False,
        xaxis_visible=False,
        template="plotly_white",
        xaxis_type = "category"
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# homepage backend
@app.route('/')
def start():
    return check_login()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()

        email = request.form['email']
        password = request.form['password']
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(generate_password_hash(user[2]), password):
            session['username'] = user[1]
            return jsonify({"success": True, "message": "Login successful"})
        else:
            return jsonify({"success": False, "message": "Invalid email or password"})
        
    return render_template('login.html')

def is_valid_email(email):
    regex = r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$'
    return re.match(regex, email)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        confirm_email = request.form['confirm_email']
        password = request.form['password']

        if email != confirm_email:
            return jsonify({"success": False, "message": "Emails do not match."})

        if not is_valid_email(email):
            return jsonify({"success": False, "message": "Invalid email format."})

        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Email already registered."})

        hashed_password = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_password))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Registration successful!"})
    return render_template('register.html')


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({"success": False, "message": "Email not registered."})

        verification_code = str(random.randint(100000, 999999))
        session['verification_code'] = verification_code
        session['reset_email'] = email
        send_verification_email(email, verification_code)
        return jsonify({"success": True, "message": "Verification code sent to email."})

    if request.method == 'GET':
        code = request.args.get('code')
        new_password = request.args.get('new_password')

        if code and new_password:
            if code == session.get('verification_code'):
                email = session.get('reset_email')
                hashed_password = generate_password_hash(new_password)
                conn = sqlite3.connect('tickers.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))
                conn.commit()
                conn.close()
                session.pop('verification_code', None)
                session.pop('reset_email', None)
                return jsonify({"success": True, "message": "Password reset successful."})
            else:
                return jsonify({"success": False, "message": "Invalid verification code."})
    return render_template('forgot.html')

@app.route('/home')
def home():
    check_login()
    headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": "PK9XXY01BXT1F6L9EFZ4",
            "APCA-API-SECRET-KEY": "vdlBS5PgF4Lp7SgyYm42MCF5jm8JUlpPMEGvLnT3"
    }
    symbol_data = [
        {"symbol": "", "name": "", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
        {"symbol": "", "name": "", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
        {"symbol": "", "name": "", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0},
    ]
    for data in symbol_data:
        url = f"https://data.alpaca.markets/v1beta1/screener/stocks/most-actives?by=trades&top=10"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error fetching data: {response.text}")
            return render_template('index.html', stocks=symbol_data)
        
        results = response.json().get("most_actives", [])
        selected_result = None
        while not selected_result or any(d["symbol"] == selected_result["symbol"] for d in symbol_data):
            selected_result = results[random.randint(0, len(results) - 1)]
        data["symbol"] = selected_result["symbol"]
        data["name"] = search_stocks(data["symbol"])[0].get("Name")
        print(search_stocks(data["symbol"])[0].get("Name"))
        data["volume"] = f'{(selected_result["volume"] / 1000000):.2f}'
        
        today = datetime.now().strftime('%Y-%m-%dT00:00:00Z')
        yesterday = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%dT00:00:00Z')
        url = f"https://data.alpaca.markets/v2/stocks/{data['symbol']}/bars?timeframe=5T&start={yesterday}&end={today}&limit=1000&adjustment=raw&feed=iex&sort=asc"
        response = requests.get(url, headers=headers)
        results = response.json().get('bars', [])
        data["price"] = f'{results[0]["c"]:.2f}'
        data["percent"] = f'{(((results[0]["c"] - results[0]["o"]) / results[1]["o"]) * 100):.2f}'
        data["high"] = f'{results[0]["h"]:.2f}'
        data["low"] = f'{results[0]["l"]:.2f}'
        
        portfolios_data = []
    
    return render_template('index.html', stocks=symbol_data, portfolios=portfolios_data)

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
    return render_template('portfolios.html')

# to be removed
@app.route('/remove')
def remove_stocks():
    return render_template('removes.html')

# retrieving graph data from API
@app.route('/spiaa', methods=['GET', 'POST'])
def spiaa():
    check_login()
    if request.method == 'POST' and 'timeframe' in request.form:
        timeframe = request.form.get('timeframe')
        print(timeframe)
        if timeframe:
            print("timeframe", timeframe)
        else:
            timeframe = '1W'
    else:
        timeframe = '1W'
        
    conn = sqlite3.connect('tickers.db')
    cursor = conn.cursor()

    command = """
        SELECT symbol, name FROM stock_history
        ORDER BY rowid DESC LIMIT 1
        """
    cursor.execute(command)
    result = cursor.fetchone()
    
    # command = """
    #     SELECT stocks_owned FROM portfolios
    #     JOIN users, tickers
    #     ON portfolios.user_id = users.user_id
    #     AND portfolios.symbol = tickers.symbol
    #     WHERE users.username = ?
    #     AND tickers.symbol = ?
    #     """
    # cursor.execute(command, (session['username'], result[0]))
    # owned = cursor.fetchall()
    # owned = sum(x for x in owned)
    conn.close()

    if result:
        session['symbol'], session['name'] = result
    else:
        return jsonify({"error": "No stock found in history"}), 404
    
    symbol = session.get('symbol', '').strip()
    name = session.get('name', '').strip()
    
    
    data = fetch_api_data(symbol, '1Y') # for fetching first 3 analysis
    analysis = [None for _ in range(12)]
    # analysis.append(owned) #stocks owned
    results = data.get('bars', [])
    #Price analysis
    analysis[1]=(results[0]['c'])
    analysis[2]=(f'{results[0]["l"]:.2f} - {results[0]["h"]:.2f}')
    analysis[3]=(f"{min(entry['l'] for entry in results)} - {max(entry['h'] for entry in results)}")
    
    #Trend indicators
    data = fetch_api_data(symbol, timeframe)
    results = data.get('bars', [])                                                                                                                                                                                                                                                                                      #secretcommentdawsabiniser
    prices = [entry["c"] for entry in results]
    period = len(prices)
    analysis[4]=(f'{sum(prices) / period:.2f}') #latest sma
    multiplier = 2 / (period + 1)
    analysis[5]=(f'{(prices[0] - (sum(prices) / period)) * multiplier + prices[0]:.2f}')
    def calculate_macd(prices, slow=26, fast=12, signal=9):
        if len(prices) < slow:
            return None, None, None  # Not enough data to calculate MACD

        def ema(prices, period):
            k = 2 / (period + 1)
            ema_values = [sum(prices[:period]) / period]
            for price in prices[period:]:
                ema_values.append(price * k + ema_values[-1] * (1 - k))
            return ema_values

        ema_fast = ema(prices, fast)
        ema_slow = ema(prices, slow)
        macd_line = [fast - slow for fast, slow in zip(ema_fast[-len(ema_slow):], ema_slow)]
        signal_line = ema(macd_line, signal)
        macd_histogram = [macd - signal for macd, signal in zip(macd_line[-len(signal_line):], signal_line)]

        return macd_line, signal_line, macd_histogram

    macd_line, signal_line, macd_histogram = calculate_macd(prices)
    analysis[6] = f'Signal line: {signal_line[-1]:.2f}'
    
    def calculate_rsi(prices, period=14):
        if len(prices) < period:
            return None  # Not enough data to calculate RSI

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi = []
        for i in range(period, len(prices)):
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi.append(100 - (100 / (1 + rs)))

        return rsi

    rsi_values = calculate_rsi(prices)
    analysis[7] = f'{rsi_values[-1]:.2f}' if rsi_values else 'RSI: N/A'
    #Risk and volatility
    
    #Valuation
    
    #Support and resistance
    
       
    chart_data = prepare_candle_plot(data)
    
    
    
    return render_template('spiaalatest.html', data=analysis, name=name, symbol=symbol, chart_data=chart_data)

@app.route('/set_stock') 
def set_stock():
    symbol = request.args.get('symbol', '').strip()
    name = request.args.get('name', '').strip()
    conn = sqlite3.connect('tickers.db')
    cursor = conn.cursor()
    
    command = """
            INSERT INTO stock_history (symbol, name)
            VALUES (?, ?) 
            """
    cursor.execute(command, (f'{symbol}', f'{name}'))
    conn.commit()
    conn.close()
    session['symbol'], session['name'] = symbol, name
    return jsonify({"message": "Stock set in session"}), 200

@app.errorhandler(Exception)
def handle_errors(e):
    return render_template('error.html', error_message=e), 500

if __name__ == '__main__':
    app.run(debug=True)
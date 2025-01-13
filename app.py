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
import pandas as pd
from flask_mailman import Mail, EmailMessage

mail = Mail()

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


def calculate_sma(prices, period):
    if len(prices) < period:
        return None  # Not enough data to calculate SMA
    sma = []
    for i in range(len(prices) - period + 1):
        sma.append(sum(prices[i:i + period]) / period)
    return sma

def calculate_bollinger_bands(prices, period=20, num_std_dev=2):
    if len(prices) < period:
        return None, None, None  # Not enough data to calculate Bollinger Bands

    sma = calculate_sma(prices, period)
    std_dev = [pd.Series(prices[i:i + period]).std() for i in range(len(prices) - period + 1)]
    upper_band = [sma[i] + num_std_dev * std_dev[i] for i in range(len(sma))]
    lower_band = [sma[i] - num_std_dev * std_dev[i] for i in range(len(sma))]
    return upper_band, sma, lower_band

def calculate_volume_analysis(prices, volumes):
    pvi = [1000]  # Positive Volume Index
    nvi = [1000]  # Negative Volume Index

    for i in range(1, len(prices)):
        if volumes[i] > volumes[i - 1]:
            pvi.append(pvi[-1] + (prices[i] - prices[i - 1]) / prices[i - 1] * pvi[-1])
            nvi.append(nvi[-1])
        else:
            nvi.append(nvi[-1] + (prices[i] - prices[i - 1]) / prices[i - 1] * nvi[-1])
            pvi.append(pvi[-1])

    return pvi, nvi

def calculate_support_resistance(prices):
    pivot = (max(prices) + min(prices) + prices[-1]) / 3
    resistance = 2 * pivot - min(prices)
    support = 2 * pivot - max(prices)
    return support, resistance

# search suggestion logic
def search_stocks(query):
    try:
        with sqlite3.connect('tickers.db') as conn:
            cursor = conn.cursor()
            
            # First, search for exact matches
            command_exact = """
                SELECT Symbol, Name FROM tickers
                WHERE Symbol = ? OR Name = ?
                LIMIT 15
            """
            cursor.execute(command_exact, (query, query))
            exact_results = cursor.fetchall()
            
            # If exact matches are found, return them
            if exact_results:
                return [{'Symbol': symbol, 'Name': name} for symbol, name in exact_results]
            
            # If no exact matches, search for partial matches
            command_partial = """
                SELECT Symbol, Name FROM tickers
                WHERE Symbol LIKE ? OR Name LIKE ?
                LIMIT 15
            """
            cursor.execute(command_partial, (f'%{query}%', f'%{query}%'))
            partial_results = cursor.fetchall()
            
            results_dict = [{'Symbol': symbol, 'Name': name} for symbol, name in partial_results]
            results_dict.sort(key=lambda x: (query.lower() not in x['Symbol'].lower(), query.lower() not in x['Name'].lower()))
            return results_dict
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return []

# api fetching logic
def fetch_api_data(symbol, timeframe):
    day = {'1W': [7, '15T'], '1M': [30, '1H'], '1Y': [365, '1D'], '5Y': [1825, '1W']}
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

def prepare_candle_plot(data, sma=None, ema=None, macd=None, rsi=None, bollinger=None, volume=None, support_resistance=None):
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

    if support_resistance:
        fig.add_trace(go.Scatter(
            x=[dates[0], dates[-1]],
            y=[support_resistance['support'], support_resistance['support']],
            mode='lines',
            name='Support',
            line=dict(color='green', width=2, dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=[dates[0], dates[-1]],
            y=[support_resistance['resistance'], support_resistance['resistance']],
            mode='lines',
            name='Resistance',
            line=dict(color='red', width=2, dash='dash')
        ))

    if bollinger:
        fig.add_trace(go.Scatter(
            x=dates,
            y=bollinger['upper_band'],
            mode='lines',
            name='Upper Band',
            line=dict(color='rgba(255, 0, 0, 0.5)')
        ))
        fig.add_trace(go.Scatter(
            x=dates,
            y=bollinger['middle_band'],
            mode='lines',
            name='Middle Band',
            line=dict(color='rgba(0, 255, 0, 0.5)')
        ))
        fig.add_trace(go.Scatter(
            x=dates,
            y=bollinger['lower_band'],
            mode='lines',
            name='Lower Band',
            line=dict(color='rgba(0, 0, 255, 0.5)')
        ))

    if volume:
        fig.add_trace(go.Scatter(
            x=dates,
            y=volume['pvi'],
            mode='lines',
            name='Positive Volume Index',
            line=dict(color='rgba(255, 165, 0, 0.5)')
        ))
        fig.add_trace(go.Scatter(
            x=dates,
            y=volume['nvi'],
            mode='lines',
            name='Negative Volume Index',
            line=dict(color='rgba(75, 0, 130, 0.5)')
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

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USERNAME'] = 'swiiftstock@gmail.com'
    app.config['MAIL_PASSWORD'] = 'ypmljcycrbfvidha'
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USE_TLS'] = False

    mail.init_app(app)
    
    def check_login():
        if 'username' not in session:
            return login()
        return None

    # homepage backend
    @app.route('/')
    def start():
        return redirect(url_for('home'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if "username" in session:
            conn = sqlite3.connect('tickers.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO user_history (username) VALUES (?)", (session['username'],))
            conn.commit()
            conn.close()
            return home()
        if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
            conn = sqlite3.connect('tickers.db')
            cursor = conn.cursor()

            email = request.form['email']
            password = request.form['password']
            
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()

            if user and check_password_hash((user[2]), password):
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
        if request.method == 'POST' and 'cf' in request.form:
            username = request.form.get('un')
            email = request.form.get('em')
            password = request.form.get('pw')
            cf = request.form.get('cf')

            conn = sqlite3.connect('tickers.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if user:
                return jsonify({"success": False, "message": "Email already registered."})
            
            code = str(random.randint(100000, 999999))
            msg = EmailMessage(
                "Verification Code For SwiftStock",
                f"Here is SwiftStock verification code: {code}",
                "swiiftstock@gmail.com",
                [f"{email}"]
            )
            msg.send()
            session['code'] = code
            session['method'] = 'register'
            return verify(email, username, password)
        return render_template('register.html')

    @app.route('/verify', methods=['GET', 'POST'])
    def verify(email = None, username = None, password = None):
        if request.method == 'POST':
            code = request.form.get('code')
            if code == session.get('code'):
                if session['method'] == 'register':
                    hashed_password = generate_password_hash(password)
                    conn = sqlite3.connect('tickers.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_password))
                    conn.commit()
                    conn.close()
                    session.pop('code', None)
                    session.pop('method', None)
                    redirect(url_for('login'))
                    return jsonify({"success": True, "message": "Registration successful."})
                elif session['method'] == 'forgot':
                    hashed_password = generate_password_hash(password)
                    conn = sqlite3.connect('tickers.db')
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))
                    conn.commit()
                    conn.close()
                    session.pop('code', None)
                    session.pop('method', None)
                    redirect(url_for('login'))
                    return jsonify({"success": True, "message": "Verification successful."})
            else:
                return jsonify({"success": False, "message": "Invalid verification code."})
        return render_template('verify.html')
    
    @app.route('/forgot', methods=['GET', 'POST'])
    def forgot():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['new_password']
            conn = sqlite3.connect('tickers.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()

            if not user:
                return jsonify({"success": False, "message": "Email not registered."})

            code = str(random.randint(100000, 999999))
            msg = EmailMessage(
                "Verification Code For SwiftStock",
                f"Here is SwiftStock verification code: {code}",
                "swiiftstock@gmail.com",
                [f"{email}"]
            )
            msg.send()
            session['code'] = code
            session['method'] = 'forgot'
            return verify(email, password=password)

        return render_template('forgot.html')

    @app.route('/home')
    def home():
        check_login()
        headers = {
                "accept": "application/json",
                "APCA-API-KEY-ID": "PK9XXY01BXT1F6L9EFZ4",
                "APCA-API-SECRET-KEY": "vdlBS5PgF4Lp7SgyYm42MCF5jm8JUlpPMEGvLnT3"
        }
        symbol_data = [{"symbol": "", "name": "", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0} for _ in range(12)]
        url = f"https://data.alpaca.markets/v1beta1/screener/stocks/most-actives?by=trades&top=20"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error fetching data: {response.text}")
            return render_template('index.html', stocks=symbol_data)
        
        sample = response.json().get("most_actives", [])
        os.system('cls')
        sample = random.sample(sample, 12)
        for data in symbol_data:
            selected_result = sample.pop()
            print(selected_result)
            data["symbol"] = selected_result["symbol"]
            data["name"] = search_stocks(data["symbol"])[0].get("Name")
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
    @app.route('/stock_monitoring')
    def stock_monitoring():
        check_login()
        if session.get('username') is None:
            conn = sqlite3.connect('tickers.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM user_history ORDER BY id DESC LIMIT 1")
            user = cursor.fetchone()
            conn.close()
            if user:
                session['username'] = user[0]
            else:
                return redirect(url_for('login'))
        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()
        cursor.execute("SELECT symbol FROM monitoring JOIN users ON users.user_id = monitoring.user_id WHERE users.username = ?", (session.get('username'),))
        res = cursor.fetchall()
        conn.close()
        res = [result[0] for result in res]
        headers = {
                "accept": "application/json",
                "APCA-API-KEY-ID": "PK9XXY01BXT1F6L9EFZ4",
                "APCA-API-SECRET-KEY": "vdlBS5PgF4Lp7SgyYm42MCF5jm8JUlpPMEGvLnT3"
        }
        symbol_data = [{"symbol": "", "name": "", "price": 0, "percent": 0, "high": 0, "low": 0, "volume": 0} for _ in range(len(res))]
        i = 0
        for data in symbol_data:
            print(res[i])
            data["symbol"] = res[i]
            i +=1
            stock_info = search_stocks(data["symbol"])
            if stock_info:
                data["name"] = stock_info[0].get("Name")
            print(stock_info)
            
            today = datetime.now().strftime('%Y-%m-%dT00:00:00Z')
            yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%dT00:00:00Z')
            url = f"https://data.alpaca.markets/v2/stocks/{data['symbol']}/bars?timeframe=1H&start={yesterday}&end={today}&limit=1000&adjustment=raw&feed=iex&sort=asc"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                results = response.json().get('bars', [])
                if results:
                    data["price"] = f'{results[0]["c"]:.2f}'
                    data["percent"] = f'{(((results[0]["c"] - results[0]["o"]) / results[1]["o"]) * 100):.2f}'
                    data["high"] = f'{results[0]["h"]:.2f}'
                    data["low"] = f'{results[0]["l"]:.2f}'
                    data["volume"] = f'{(results[0]["v"] / 1000000):.2f}'
        
        lines = [fetch_api_data(symbol, '1W') for symbol in res]
        def prepare_line_graph(data):
            fig = go.Figure()
            for i in range(len(res)):
                results = data[i].get('bars', [])
                dates = [entry["t"] for entry in results]
                dates = [datetime.strptime(entry["t"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8) for entry in results]
                close_prices = [entry["c"] for entry in results]
                fig.add_trace(go.Scatter(x=dates, y=close_prices, mode='lines', name=res[i]))
        
        chart_data = prepare_line_graph(lines)
        
        
        return render_template('stockmonitoring.html', stocks=symbol_data, chart_data=chart_data)

    # retrieving graph data from API
    @app.route('/spiaa', methods=['GET', 'POST'])
    def spiaa():
        check_login()
        if session.get('username') is None:
            conn = sqlite3.connect('tickers.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM user_history ORDER BY id DESC LIMIT 1")
            user = cursor.fetchone()
            conn.close()
            if user:
                session['username'] = user[0]
            else:
                return redirect(url_for('login'))
        if request.method == 'POST' and 'timeframe' in request.form:
            timeframe = request.form.get('timeframe')
            print(timeframe)
            if timeframe:
                os.system('cls')
                print("timeframe", timeframe)
            else:
                timeframe = '1W'
        else:
            timeframe = '1W'
        user = session.get('username')    
        print(user)
        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()
        command = """
            SELECT symbol, name FROM stock_history
            ORDER BY rowid DESC LIMIT 1 
            """
        cursor.execute(command)
        result = cursor.fetchone()
        conn.close()
        

        if result:
            session['symbol'], session['name'] = result
        else:
            return jsonify({"error": "No stock found in history"}), 404
        
        symbol = session.get('symbol', '').strip()
        name = session.get('name', '').strip()
        
        
        data = fetch_api_data(symbol, '1Y') # for fetching first 3 analysis
        analysis = ["" for _ in range(12)]
        # analysis.append(owned) #stocks owned
        results = data.get('bars', [])
        
        #Price analysis
        analysis[1]=(results[0]['c'])
        analysis[2]=(f'{results[0]["l"]:.2f} - {results[0]["h"]:.2f}')
        analysis[3]=(f"{min(entry['l'] for entry in results)} - {max(entry['h'] for entry in results)}")
        
        #Trend indicators
        data = fetch_api_data(symbol, timeframe)

        #Risk and volatility
        # Define dates
        dates = [entry["t"] for entry in results]
        dates = [datetime.strptime(entry["t"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8) for entry in results]
        close_prices = [entry["c"] for entry in results]

        # Bollinger Bands
        upper_band, middle_band, lower_band = calculate_bollinger_bands(close_prices)
    
        # Volume Analysis
        volumes = [entry["v"] for entry in results]
        pvi, nvi = calculate_volume_analysis(close_prices, volumes)
    
        # Support and Resistance
        support, resistance = calculate_support_resistance(close_prices)
    
        chart_data = prepare_candle_plot(data, sma=None, ema=None, macd=None, rsi=None, bollinger={
            'upper_band': upper_band,
            'middle_band': middle_band,
            'lower_band': lower_band
        }, volume={
            'pvi': pvi,
            'nvi': nvi
        }, support_resistance={
            'support': support,
            'resistance': resistance
        })
        
        # Check if the symbol is in the monitoring table for the user
        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM monitoring JOIN users ON users.user_id = monitoring.user_id WHERE users.username = ? AND symbol = ?", (session['username'], symbol))
        is_monitored = cursor.fetchone() is not None
        conn.close()
        
        return render_template('spiaalatest.html', data=analysis, symbol=symbol, name=name, analysis=analysis, chart_data=chart_data, is_monitored=is_monitored)
   
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

    @app.route('/toggle_monitor', methods=['POST'])
    def toggle_monitor():
        symbol = request.form.get('symbol')
        username = session.get('username')
        
        if username is None:
            conn = sqlite3.connect('tickers.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM user_history ORDER BY id DESC LIMIT 1")
            username = cursor.fetchone()
            conn.close()    
        
        if not symbol or not username:
            return jsonify({"success": False, "message": "Invalid request"}), 400
        
        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM monitoring JOIN users ON users.user_id = monitoring.user_id WHERE users.username = ? AND symbol = ?", (username, symbol))
        is_monitored = cursor.fetchone() is not None
        
        if is_monitored:
            cursor.execute("DELETE FROM monitoring WHERE user_id = (SELECT user_id FROM users WHERE username = ?) AND symbol = ?", (username, symbol))
            message = "Removed from monitoring"
        else:
            cursor.execute("INSERT INTO monitoring (user_id, symbol) VALUES ((SELECT user_id FROM users WHERE username = ?), ?)", (username, symbol))
            message = "Added to monitoring"
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": message})
    
    
    # @app.errorhandler(Exception)
    # def handle_errors(e):
    #     return render_template('error.html', error_message=e), 500

    return app
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
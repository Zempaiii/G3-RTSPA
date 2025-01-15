from flask import request, jsonify, Flask, render_template, session, redirect, url_for, flash
import os, sqlite3, requests, plotly, random
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import re
import plotly.graph_objects as go
from dotenv import load_dotenv
import json
import pandas as pd
from flask_mailman import Mail, EmailMessage

mail = Mail()

app = Flask(__name__)
app.secret_key = os.urandom(24)

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
def fetch_api_data(symbol, timeframe, offset = 0):
    day = {'1W': [7, '15T'], '1M': [30, '1H'], '1Y': [365, '1D'], '5Y': [1825, '1W']}
    day = day.get(timeframe)
    end = datetime.now().strftime('%Y-%m-%dT00:00:00Z')
    offset_days = offset * {'1W': .0475, '1M': .1, '1Y': 1, '5Y': 7}[timeframe]
    start = (datetime.now() - timedelta(days=day[0] + offset_days)).strftime('%Y-%m-%dT00:00:00Z')
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

def prepare_candle_plot(data, sma_data = None, ema_data = None, bollinger_bands_data = None, macd_data = None):
    results = data.get('bars', [])
    results = results[5:-1]
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
        close=close_prices,
        name='Candlestick',
        showlegend=False
    )])
    
    if sma_data:
        sma_dates = [entry["t"] for entry in sma_data]
        sma_dates = [datetime.strptime(entry["t"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8) for entry in sma_data]
        sma_prices = [entry["sma"] for entry in sma_data]
        fig.add_trace(go.Scatter(x=sma_dates, y=sma_prices, mode='lines', name='SMA', line=dict(color='blue')))
        
    if ema_data:
        ema_dates = [entry["t"] for entry in ema_data]
        ema_dates = [datetime.strptime(entry["t"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8) for entry in ema_data]
        ema_prices = [entry["ema"] for entry in ema_data]
        fig.add_trace(go.Scatter(x=ema_dates, y=ema_prices, mode='lines', name='EMA', line=dict(color='red')))
    
    if bollinger_bands_data:
        middle_dates = [entry["t"] for entry in bollinger_bands_data]
        middle_dates = [datetime.strptime(entry["t"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8) for entry in bollinger_bands_data]
        middle_prices = [entry["middle_band"] for entry in bollinger_bands_data]
        upper_prices = [entry["upper_band"] for entry in bollinger_bands_data]
        lower_prices = [entry["lower_band"] for entry in bollinger_bands_data]
        fig.add_trace(go.Scatter(x=middle_dates, y=middle_prices, mode='lines', name='Middle Band', line=dict(color='black')))
        fig.add_trace(go.Scatter(x=middle_dates, y=upper_prices, mode='lines', name='Upper Band', line=dict(color='green')))
        fig.add_trace(go.Scatter(x=middle_dates, y=lower_prices, mode='lines', name='Lower Band', line=dict(color='red')))
    
    if macd_data:
        macd_dates = [entry["t"] for entry in macd_data]
        macd_dates = [datetime.strptime(entry["t"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8) for entry in macd_data]
        macd_prices = [entry["macd"] for entry in macd_data]
        signal_prices = [entry["signal"] for entry in macd_data]
        fig.add_trace(go.Scatter(x=macd_dates, y=macd_prices, mode='lines', name='MACD', line=dict(color='purple')))
        fig.add_trace(go.Scatter(x=macd_dates, y=signal_prices, mode='lines', name='Signal', line=dict(color='black')))
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False,
        xaxis_visible=False,
        template="plotly_white",
        xaxis_type = "category"
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def prepare_line_graph(data, res):
    data = [data.get('bars', []) for data in data]
    fig = go.Figure()
    i = 0
    for line in data:
        if line:
            fig.add_trace(go.Scatter(
                x=[entry["t"] for entry in line],
                y=[entry["c"] for entry in line],
                mode='lines',
                name=res[i]
            ))
        i += 1
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False,
        xaxis_visible=False,
        template="plotly_white",
        xaxis_type="category"
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def calculate_sma(data):
    results = data.get('bars', [])
    chart_data = [{"t": entry["t"], "c": entry["c"], "sma": 0} for entry in results[5:-1]]
    
    for i in range(0, len(chart_data)):
        sma = sum(entry["c"] for entry in results[i:i + 5]) / 5
        chart_data[i]["sma"] = sma

    return chart_data

def calculate_ema(data):
    results = data.get('bars', [])
    chart_data = [{"t": entry["t"], "c": entry["c"], "ema": 0} for entry in results[5:-1]]
    
    sma = sum(entry["c"] for entry in results[0:0 + 5]) / 5
    alpha = 2 / (5 + 1)
    
    chart_data[0]["ema"] = sma
    
    for i in range (1, len(chart_data)):
        ema = (chart_data[i]["c"] * alpha) + (chart_data[i-1]["ema"] * (1 - alpha))
        chart_data[i]["ema"] = ema
        
    print("ema", len(chart_data))
    return chart_data

def rsi_data(data):
    results = data.get('bars', [])
    chart_data = [{"t": entry["t"], "c": entry["c"], "rsi": 0} for entry in results[14:]]

    for i in range(len(chart_data)):
        gains = []
        losses = []
        for j in range(i, i + 14):
            change = results[j + 1]["c"] - results[j]["c"]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        
        average_gain = sum(gains) / 14
        average_loss = sum(losses) / 14
        rs = average_gain / average_loss if average_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        chart_data[i]["rsi"] = rsi

    return chart_data[-1]['rsi']

def calculate_bollinger(data):
    results = data.get('bars', [])
    chart_data = [{"t": entry["t"], "c": entry["c"], "middle_band": 0, "upper_band":0, "lower_band": 0} for entry in results[19:]]
    
    for i in range(0, len(chart_data)):
        sma = sum(entry["c"] for entry in results[i:i+20]) / 20
        chart_data[i]["middle_band"] = sma
        
        stdev = (sum((entry["c"] - sma) ** 2 for entry in results[i:i+20]) / 20) ** 0.5
        chart_data[i]["upper_band"] = sma + (2 * stdev)
        chart_data[i]["lower_band"] = sma - (2 * stdev)
    
    return chart_data        

def create_app():
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
        return redirect(url_for('login'))

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
            session['email'] = email
            session['username'] = username
            session['password'] = password
            return jsonify({"success": True, "message": "Verification code sent. Redirecting to verification page."})
        return render_template('register.html')

    @app.route('/verify', methods=['GET', 'POST'])
    def verify(email = None, username = None, password = None):
        if request.method == 'POST':
            code = request.form.get('code')
            if code == session.get('code'):
                if session['method'] == 'register':
                    hashed_password = generate_password_hash(session['password'])
                    conn = sqlite3.connect('tickers.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (session['username'], session['email'], hashed_password))
                    conn.commit()
                    conn.close()
                    session.pop('code', None)
                    session.pop('method', None)
                    return jsonify({"success": True, "message": "Registration successful."})
                elif session['method'] == 'forgot':
                    hashed_password = generate_password_hash(session['password'])
                    conn = sqlite3.connect('tickers.db')
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, session['email']))
                    conn.commit()
                    conn.close()
                    session.pop('code', None)
                    session.pop('method', None)
                    return jsonify({"success": True, "message": "Verification successful."})
            else:
                return jsonify({"success": False, "message": "Invalid verification code."})
        return render_template('verify.html')
    
    @app.route('/forgot', methods=['GET', 'POST'])
    def forgot():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('new_password')
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
            session['email'] = email
            session['password'] = password
            return jsonify({"success": True, "message": "Verification code sent. Redirecting to verification page."})

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
        
        lines = [fetch_api_data(symbol, '5Y') for symbol in res]
        chart_data = prepare_line_graph(lines, res)
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
            if timeframe:
                os.system('cls')
                print("timeframe", timeframe)
            else:
                timeframe = '1W'
        else:
            timeframe = '1W'
        user = session.get('username') 
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
        
        data = fetch_api_data(symbol, timeframe)
        
        data = fetch_api_data(symbol, '1Y') # for fetching first 3 analysis
        
        analysis = ["" for _ in range(12)]
        results = data.get('bars', [])
        
        #Price analysis
        analysis[1]=(results[0]['c'])
        analysis[2]=(f'{results[0]["l"]:.2f} - {results[0]["h"]:.2f}')
        analysis[3]=(f"{min(entry['l'] for entry in results)} - {max(entry['h'] for entry in results)}")
        
        data = fetch_api_data(symbol, timeframe, 5)
        sma_data = calculate_sma(data)
        ema_data = calculate_ema(data)
        analysis[4] = f'{sma_data[-1]["sma"]:.2f}'
        analysis[5] = f'{ema_data[-1]["ema"]:.2f}'
        
        data = fetch_api_data(symbol, timeframe, 20)
        bollinger_bands_data = calculate_bollinger(data)
        
        data = fetch_api_data(symbol, timeframe, 5)
        analysis[7] = f"{rsi_data(data):.2f}"
        analysis[8] = f"{bollinger_bands_data[-1]['upper_band']:.2f}"
        analysis[9] = f"{bollinger_bands_data[-1]['middle_band']:.2f}"
        analysis[10] = f"{bollinger_bands_data[-1]['lower_band']:.2f}"
        chart_data = prepare_candle_plot(data, sma_data, ema_data, bollinger_bands_data=bollinger_bands_data)
        # Check if the symbol is in the monitoring table for the user
        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM monitoring JOIN users ON users.user_id = monitoring.user_id WHERE users.username = ? AND symbol = ?", (session['username'], symbol))
        is_monitored = cursor.fetchone() is not None
        conn.close()
        
        return render_template('spiaalatest.html', name=session['name'], symbol=session['symbol'], data=analysis, chart_data=chart_data, is_monitored=is_monitored)
   
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
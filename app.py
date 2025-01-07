from flask import request, jsonify, Flask, render_template, session, redirect, url_for
import os, sqlite3, requests, plotly, random
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash
import re
import plotly.graph_objects as go
from dotenv import load_dotenv
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)



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
def fetch_api_data(symbol):
    end = datetime.now().strftime('%Y-%m-%dT00:00:00Z')
    start = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00Z')
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?timeframe=5T&start={start}&end={end}&limit=1000&adjustment=raw&feed=iex&sort=asc"
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
    return login()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials')
            return render_template('login.html')
    return render_template('login.html')

def is_valid_email(email):
    regex = r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$'
    return re.match(regex, email)

@app.route('/register', methods=['GET' , 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        confirm_email = request.form['confirm_email']

        if not is_valid_email(email):
            flash('Invalid email format')
            return render_template('register.html')

        if email != confirm_email:
            flash('Emails do not match')
            return render_template('register.html')

        conn = sqlite3.connect('tickers.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            flash('Email already registered')
            return render_template('register.html')
        
        # Send validation email using Mailtrap
        msg = MIMEText('Please validate your email')
        msg['Subject'] = 'Email Validation'
        msg['From'] = 'swiiftstock@gmail.com'
        msg['To'] = email

        with smtplib.SMTP('smtp.mailtrap.io', 2525) as server:
            server.login('your_mailtrap_username', 'your_mailtrap_password')
            server.sendmail(msg['From'], [msg['To']], msg.as_string())

        # Add user to database
        hashed_password = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_password))
        conn.commit()
        conn.close()

        flash('Registration successful, please check your email for validation')
        return redirect(url_for('login'))
    
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

        if user:
            # Send verification email using Mailtrap
            msg = MIMEText('Please validate your email to reset your password')
            msg['Subject'] = 'Password Reset'
            msg['From'] = 'your-email@example.com'
            msg['To'] = email

            with smtplib.SMTP('smtp.mailtrap.io', 2525) as server:
                server.login('your_mailtrap_username', 'your_mailtrap_password')
                server.sendmail(msg['From'], [msg['To']], msg.as_string())

            flash('Verification email sent, please check your email')
            return redirect(url_for('login'))
        else:
            flash('No account found with that email')
            return render_template('forgot.html')
        
    return render_template('forgot.html')

@app.route('/home')
def home():
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
        yesterday = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00Z')
        url = f"https://data.alpaca.markets/v2/stocks/{data['symbol']}/bars?timeframe=5T&start={yesterday}&end={today}&limit=1000&adjustment=raw&feed=iex&sort=asc"
        response = requests.get(url, headers=headers)
        results = response.json().get('bars', [])
        print(results)
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
    
    data = fetch_api_data(symbol) 
    if data is None or 'bars' not in data:
        return jsonify({"error": "Failed to fetch data from API"}), 500
    
    chart_data = prepare_candle_plot(data, symbol)
    
    return render_template('spiaa.html', name=name, symbol=symbol, chart_data=chart_data)

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

if __name__ == '__main__':
    app.run(debug=True)
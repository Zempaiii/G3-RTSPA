from flask import request, jsonify, Flask, render_template
import finnhub, os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('FINNHUB_API_KEY')
finnhub_client = finnhub.Client(api_key=api_key)

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/preview')
def preview():
    return render_template('preview.html')

@app.route('/add')
def add_stocks():
    return render_template('adds.html')

@app.route('/remove')
def remove_stocks():
    return render_template('removes.html')

if __name__ == '__main__':
    app.run(debug=True)
    
if __name__ == '__main__':
  app.run(debug=True)
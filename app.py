from flask import request, jsonify, Flask
import finnhub, os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('FINNHUB_API_KEY')
finnhub_client = finnhub.Client(api_key=api_key)

app = Flask(__name__)

@app.route('/')
def home():
  news = finnhub_client.general_news('general', min_id=0)
  return jsonify(news)

if __name__ == '__main__':
  app.run(debug=True)
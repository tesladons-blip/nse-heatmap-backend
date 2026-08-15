from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample market data (replace with real data later)
SAMPLE_DATA = [
    {'name': 'IT', 'value': 2.5, 'stocks': 7, 'size': 560},
    {'name': 'FINANCE', 'value': -0.8, 'stocks': 7, 'size': 560},
    {'name': 'AUTO', 'value': 1.2, 'stocks': 3, 'size': 240},
    {'name': 'PHARMA', 'value': 3.2, 'stocks': 4, 'size': 320},
    {'name': 'FMCG', 'value': 0.3, 'stocks': 4, 'size': 320},
    {'name': 'ENERGY', 'value': -1.5, 'stocks': 3, 'size': 240},
    {'name': 'REALTY', 'value': 0.8, 'stocks': 3, 'size': 240},
    {'name': 'METALS', 'value': -2.5, 'stocks': 4, 'size': 320},
]

def get_color(value):
    if value > 2:
        return '#10b981'
    elif value > 0.5:
        return '#6ee7b7'
    elif value > -0.5:
        return '#9ca3af'
    elif value > -2:
        return '#fca5a5'
    else:
        return '#ef4444'

# Add colors to sample data
for sector in SAMPLE_DATA:
    sector['color'] = get_color(sector['value'])

cache = {
    'data': SAMPLE_DATA,
    'timestamp': datetime.now().isoformat()
}

@app.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    logger.info(f"API call: /api/heatmap - returning {len(cache['data'])} sectors")
    return jsonify({
        'data': cache['data'],
        'timestamp': cache['timestamp'],
        'count': len(cache['data'])
    })

@app.route('/api/refresh', methods=['POST'])
def manual_refresh():
    logger.info("Manual refresh requested")
    return jsonify({
        'status': 'refreshed',
        'timestamp': cache['timestamp'],
        'data': cache['data']
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'cached_at': cache['timestamp'],
        'sectors': len(cache['data'])
    })

if __name__ == '__main__':
    logger.info("="*50)
    logger.info("NSE Heatmap Backend - Sample Data Version")
    logger.info(f"Ready to serve {len(SAMPLE_DATA)} sectors")
    logger.info("="*50)
    app.run(debug=False, host='0.0.0.0', port=5000)

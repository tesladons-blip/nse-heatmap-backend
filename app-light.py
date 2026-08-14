from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import threading
import time
import logging

app = Flask(__name__)
CORS(app)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NSE Sector Stocks
SECTORS = {
    'IT': ['TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCL.NS'],
    'FINANCE': ['HDFC.NS', 'ICICIBANK.NS', 'KOTAK.NS', 'SBIN.NS'],
    'AUTO': ['MARUTI.NS', 'BAJAJ-AUTO.NS', 'TATAMOTORS.NS'],
    'PHARMA': ['CIPLA.NS', 'SUNPHARMA.NS', 'DRREDDY.NS', 'LUPIN.NS'],
    'FMCG': ['NESTLEIND.NS', 'BRITANNIA.NS', 'ITC.NS', 'HINDUNILVR.NS'],
    'ENERGY': ['RELIANCE.NS', 'NTPC.NS', 'COALINDIA.NS'],
    'REALTY': ['DLF.NS', 'LODHA.NS', 'OBEROI.NS'],
    'METALS': ['TATASTEEL.NS', 'HINDALCO.NS', 'VEDL.NS'],
}

# Cache
cache = {
    'data': [],
    'timestamp': None
}

def fetch_sector_data():
    """Fetch EOD data for all sectors"""
    try:
        logger.info("Starting data fetch...")
        data = []
        
        for sector, stocks in SECTORS.items():
            returns = []
            valid_stocks = 0
            
            for stock in stocks:
                try:
                    # Fetch last 2 days
                    hist = yf.download(stock, period='2d', progress=False, quiet=True)
                    
                    if len(hist) >= 2:
                        close_prev = hist['Close'].iloc[-2]
                        close_curr = hist['Close'].iloc[-1]
                        daily_return = ((close_curr - close_prev) / close_prev) * 100
                        returns.append(daily_return)
                        valid_stocks += 1
                except:
                    continue
            
            if returns:
                avg_return = sum(returns) / len(returns)
                
                data.append({
                    'name': sector,
                    'size': max(50, valid_stocks * 80),
                    'value': round(avg_return, 2),
                    'stocks': valid_stocks,
                    'color': get_color(avg_return)
                })
                
                logger.info(f"{sector}: {avg_return:.2f}% ({valid_stocks} stocks)")
        
        cache['data'] = data
        cache['timestamp'] = datetime.now().isoformat()
        logger.info(f"Data fetch complete. {len(data)} sectors updated.")
        return data
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return []

def get_color(value):
    """Return color based on percentage"""
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

def scheduled_refresh():
    """Refresh daily at 4:00 PM IST"""
    while True:
        try:
            now = datetime.now()
            if now.weekday() < 5:  # Weekdays only
                target_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
                
                if now < target_time:
                    sleep_seconds = (target_time - now).total_seconds()
                    time.sleep(sleep_seconds)
                
                logger.info("Scheduled refresh triggered")
                fetch_sector_data()
            
            time.sleep(3600)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(60)

# Start background thread
refresh_thread = threading.Thread(target=scheduled_refresh, daemon=True)
refresh_thread.start()

# API Routes
@app.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    if not cache['data']:
        fetch_sector_data()
    
    return jsonify({
        'data': cache['data'],
        'timestamp': cache['timestamp'],
        'count': len(cache['data'])
    })

@app.route('/api/refresh', methods=['POST'])
def manual_refresh():
    fetch_sector_data()
    return jsonify({'status': 'refreshed', 'timestamp': cache['timestamp']})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'cached_at': cache['timestamp']})

if __name__ == '__main__':
    logger.info("App starting... fetching initial data")
    fetch_sector_data()
    app.run(debug=False, host='0.0.0.0', port=5000)

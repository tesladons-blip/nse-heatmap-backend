from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import threading
import time
import logging
import traceback

app = Flask(__name__)
CORS(app)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NSE Sector Stocks (reduced to test)
SECTORS = {
    'IT': ['TCS.NS', 'INFY.NS', 'WIPRO.NS'],
    'FINANCE': ['HDFC.NS', 'ICICIBANK.NS', 'SBIN.NS'],
    'AUTO': ['MARUTI.NS', 'BAJAJ-AUTO.NS'],
    'PHARMA': ['CIPLA.NS', 'SUNPHARMA.NS'],
    'FMCG': ['NESTLEIND.NS', 'BRITANNIA.NS'],
}

# Cache
cache = {
    'data': [],
    'timestamp': None
}

def fetch_sector_data():
    """Fetch EOD data for all sectors"""
    try:
        logger.info("=" * 50)
        logger.info("Starting data fetch...")
        data = []
        total_stocks = 0
        failed_stocks = 0
        
        for sector, stocks in SECTORS.items():
            logger.info(f"Fetching sector: {sector}")
            returns = []
            valid_stocks = 0
            
            for stock in stocks:
                try:
                    logger.info(f"  Downloading {stock}...")
                    # Try to fetch data
                    hist = yf.download(stock, period='5d', progress=False, quiet=True)
                    
                    if hist is None or len(hist) == 0:
                        logger.warning(f"  No data for {stock}")
                        failed_stocks += 1
                        continue
                    
                    if len(hist) >= 2:
                        close_prev = hist['Close'].iloc[-2]
                        close_curr = hist['Close'].iloc[-1]
                        
                        if close_prev == 0:
                            logger.warning(f"  Zero price for {stock}")
                            failed_stocks += 1
                            continue
                        
                        daily_return = ((close_curr - close_prev) / close_prev) * 100
                        returns.append(daily_return)
                        valid_stocks += 1
                        total_stocks += 1
                        logger.info(f"  ✓ {stock}: {daily_return:.2f}%")
                    else:
                        logger.warning(f"  Insufficient data for {stock}")
                        failed_stocks += 1
                        
                except Exception as e:
                    logger.error(f"  ✗ Error fetching {stock}: {str(e)}")
                    failed_stocks += 1
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
                logger.info(f"✓ {sector}: {avg_return:.2f}% ({valid_stocks} stocks)")
            else:
                logger.warning(f"✗ No data for sector: {sector}")
        
        cache['data'] = data
        cache['timestamp'] = datetime.now().isoformat()
        
        logger.info(f"Data fetch complete. {len(data)} sectors, {total_stocks} total stocks, {failed_stocks} failed")
        logger.info("=" * 50)
        return data
    
    except Exception as e:
        logger.error(f"FATAL ERROR in fetch_sector_data: {str(e)}")
        logger.error(traceback.format_exc())
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
                    logger.info(f"Next refresh at {target_time}. Sleeping for {sleep_seconds} seconds")
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
    return jsonify({
        'status': 'ok',
        'cached_at': cache['timestamp'],
        'sectors': len(cache['data'])
    })

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("App starting... fetching initial data")
    fetch_sector_data()
    logger.info("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=5000)

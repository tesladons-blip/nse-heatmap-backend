from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import threading
import time
import logging

app = Flask(__name__)
CORS(app)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NSE Sector Stocks (Top 10-15 per sector)
SECTORS = {
    'IT': ['TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCL.NS', 'TECH.NS', 'MPHASIS.NS', 'LTIM.NS'],
    'FINANCE': ['HDFC.NS', 'ICICIBANK.NS', 'KOTAK.NS', 'AXISBANK.NS', 'INDUSIND.NS', 'SBIN.NS', 'HDFCBANK.NS'],
    'AUTO': ['MARUTI.NS', 'BAJAJ-AUTO.NS', 'HYUNDAI.NS', 'TATAMOTORS.NS', 'EICHERMOT.NS', 'SUNRISEPHARMA.NS'],
    'PHARMA': ['CIPLA.NS', 'SUNPHARMA.NS', 'DRREDDY.NS', 'LUPIN.NS', 'DIVISLAB.NS', 'TORNTPHARM.NS', 'APOLLOHOSP.NS'],
    'FMCG': ['NESTLEIND.NS', 'BRITANNIA.NS', 'ITC.NS', 'HINDUNILVR.NS', 'MARICO.NS', 'COLPAL.NS', 'GODREJCP.NS'],
    'ENERGY': ['RELIANCE.NS', 'NTPC.NS', 'COALINDIA.NS', 'POWERGRID.NS', 'IOCL.NS', 'BPCL.NS'],
    'REALTY': ['DLF.NS', 'SUNTECK.NS', 'LODHA.NS', 'OBEROI.NS', 'UNITECH.NS', 'GODREJPROP.NS'],
    'TELECOM': ['JIO.NS', 'BHARTIARTL.NS', 'IDEA.NS', 'INDIGO.NS', 'SPICEJET.NS'],
    'METALS': ['TATASTEEL.NS', 'HINDALCO.NS', 'VEDL.NS', 'JSWSTEEL.NS', 'NATIONALAL.NS', 'SAIL.NS'],
    'INFRA': ['ADANIGREEN.NS', 'ADANIPORTS.NS', 'APLAPOLLO.NS', 'CUMMINSIND.NS', 'IRCTC.NS', 'SBICARD.NS']
}

# Cache for data
cache = {
    'data': [],
    'timestamp': None
}

def fetch_sector_data():
    """Fetch EOD data for all sectors and calculate metrics"""
    try:
        logger.info("Starting data fetch...")
        data = []
        
        for sector, stocks in SECTORS.items():
            returns = []
            volumes = []
            valid_stocks = 0
            
            for stock in stocks:
                try:
                    # Fetch last 5 days of data
                    hist = yf.download(stock, period='5d', progress=False, quiet=True)
                    
                    if len(hist) >= 2:
                        # Calculate daily return
                        close_prev = hist['Close'].iloc[-2]
                        close_curr = hist['Close'].iloc[-1]
                        daily_return = ((close_curr - close_prev) / close_prev) * 100
                        
                        volume = hist['Volume'].iloc[-1]
                        
                        returns.append(daily_return)
                        volumes.append(volume)
                        valid_stocks += 1
                except Exception as e:
                    logger.warning(f"Error fetching {stock}: {e}")
                    continue
            
            if returns:
                avg_return = sum(returns) / len(returns)
                total_volume = sum(volumes)
                
                data.append({
                    'name': sector,
                    'size': max(50, valid_stocks * 80),  # Size for treemap
                    'value': round(avg_return, 2),  # Color based on return
                    'stocks': valid_stocks,
                    'volume': int(total_volume),
                    'color': get_color(avg_return)
                })
                
                logger.info(f"{sector}: {avg_return:.2f}% ({valid_stocks} stocks)")
            else:
                logger.warning(f"No data for sector: {sector}")
        
        # Sort by abs value for better treemap layout
        data.sort(key=lambda x: abs(x['value']), reverse=True)
        
        cache['data'] = data
        cache['timestamp'] = datetime.now().isoformat()
        
        logger.info(f"Data fetch complete. {len(data)} sectors updated.")
        return data
    
    except Exception as e:
        logger.error(f"Fatal error in fetch_sector_data: {e}")
        return []

def get_color(value):
    """Return color based on percentage value"""
    if value > 2:
        return '#10b981'  # Strong Green
    elif value > 0.5:
        return '#6ee7b7'  # Light Green
    elif value > -0.5:
        return '#9ca3af'  # Gray
    elif value > -2:
        return '#fca5a5'  # Light Red
    else:
        return '#ef4444'  # Strong Red

def scheduled_refresh():
    """Refresh data daily at 4:00 PM IST (market close + 30 mins)"""
    while True:
        now = datetime.now()
        # Check if it's a weekday and time is 4:00 PM
        if now.weekday() < 5:  # Monday = 0, Friday = 4
            target_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
            
            if now < target_time:
                sleep_seconds = (target_time - now).total_seconds()
                logger.info(f"Next refresh at {target_time}. Sleeping for {sleep_seconds} seconds")
                time.sleep(sleep_seconds)
            
            # Refresh data
            logger.info("Scheduled refresh triggered")
            fetch_sector_data()
        
        # Sleep 1 hour and check again
        time.sleep(3600)

# Start background thread for scheduled refresh
refresh_thread = threading.Thread(target=scheduled_refresh, daemon=True)
refresh_thread.start()

# API Routes
@app.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    """Get latest heatmap data"""
    if not cache['data']:
        # If cache empty, fetch immediately
        fetch_sector_data()
    
    return jsonify({
        'data': cache['data'],
        'timestamp': cache['timestamp'],
        'count': len(cache['data'])
    })

@app.route('/api/refresh', methods=['POST'])
def manual_refresh():
    """Manually trigger refresh"""
    fetch_sector_data()
    return jsonify({'status': 'refreshed', 'timestamp': cache['timestamp']})

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'cached_at': cache['timestamp']})

if __name__ == '__main__':
    # Initial data fetch on startup
    logger.info("App starting... fetching initial data")
    fetch_sector_data()
    
    # Run Flask app
    app.run(debug=False, host='0.0.0.0', port=5000)

from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
from datetime import datetime
import logging
import traceback

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# VERIFIED NSE Sector Stocks - Only stocks that work on Yahoo Finance
SECTORS = {
    'IT': ['TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
    'FINANCE': ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'AXISBANK.NS', 'KOTAK.NS'],
    'AUTO': ['MARUTI.NS', 'TATAMOTORS.NS', 'BAJAJ-AUTO.NS'],
    'PHARMA': ['CIPLA.NS', 'SUNPHARMA.NS', 'DRREDDY.NS', 'LUPIN.NS'],
    'FMCG': ['ITC.NS', 'HINDUNILVR.NS', 'BRITANNIA.NS'],
    'ENERGY': ['RELIANCE.NS', 'NTPC.NS', 'COALINDIA.NS'],
    'METAL': ['TATASTEEL.NS', 'HINDALCO.NS', 'JSWSTEEL.NS'],
    'INFRA': ['LT.NS', 'POWERGRID.NS', 'IOCL.NS'],
}

cache = {
    'data': [],
    'timestamp': None
}

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

def fetch_sector_data():
    """Fetch real EOD data for all sectors"""
    try:
        logger.info("="*50)
        logger.info("Starting data fetch with VERIFIED tickers...")
        data = []
        total_stocks = 0
        failed_stocks = 0
        
        for sector, stocks in SECTORS.items():
            logger.info(f"\nSector: {sector}")
            returns = []
            valid_stocks = 0
            
            for stock in stocks:
                try:
                    logger.info(f"  → Downloading {stock}...")
                    hist = yf.download(stock, period='5d', progress=False)
                    
                    if hist is None or len(hist) == 0:
                        logger.warning(f"  ✗ No data for {stock}")
                        failed_stocks += 1
                        continue
                    
                    if len(hist) >= 2:
                        close_prev = hist['Close'].iloc[-2]
                        close_curr = hist['Close'].iloc[-1]
                        
                        if close_prev <= 0:
                            logger.warning(f"  ✗ Invalid price for {stock}")
                            failed_stocks += 1
                            continue
                        
                        daily_return = ((close_curr - close_prev) / close_prev) * 100
                        returns.append(daily_return)
                        valid_stocks += 1
                        total_stocks += 1
                        logger.info(f"  ✓ {stock}: {daily_return:.2f}%")
                    else:
                        logger.warning(f"  ✗ Insufficient data for {stock}")
                        failed_stocks += 1
                        
                except Exception as e:
                    logger.error(f"  ✗ Error with {stock}: {str(e)}")
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
                logger.warning(f"✗ No valid data for {sector}")
        
        cache['data'] = data
        cache['timestamp'] = datetime.now().isoformat()
        
        logger.info(f"\n✓ SUCCESS: {len(data)} sectors, {total_stocks} stocks fetched")
        logger.info(f"✗ Failed: {failed_stocks}")
        logger.info("="*50)
        return data
    
    except Exception as e:
        logger.error(f"FATAL ERROR: {str(e)}")
        logger.error(traceback.format_exc())
        return []

@app.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    if not cache['data']:
        fetch_sector_data()
    
    logger.info(f"API: /api/heatmap - {len(cache['data'])} sectors")
    return jsonify({
        'data': cache['data'],
        'timestamp': cache['timestamp'],
        'count': len(cache['data'])
    })

@app.route('/api/refresh', methods=['POST'])
def manual_refresh():
    logger.info("Manual refresh triggered")
    fetch_sector_data()
    return jsonify({
        'status': 'refreshed',
        'timestamp': cache['timestamp'],
        'sectors': len(cache['data'])
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
    logger.info("NSE Heatmap Backend - VERIFIED Tickers")
    logger.info("="*50)
    fetch_sector_data()
    app.run(debug=False, host='0.0.0.0', port=5000)

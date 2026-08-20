# api.py - Complete Vercel Host Ready Code
# Just copy this single file and deploy on Vercel

import json
import requests
from datetime import datetime
import random
from collections import deque

# ==================== STORAGE ====================
history_logs = deque(maxlen=50)
current_prediction = None
last_period = None

# ==================== FETCH EXTERNAL DATA ====================
def fetch_external_data():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        if not data.get('data', {}).get('list'):
            return None
        return data
    except:
        return None

# ==================== PREDICTION LOGIC ====================
def determine_prediction(history):
    trend = history[:3]
    big_count = sum(1 for entry in trend if entry['number'] >= 5)
    prediction = 'BIG' if big_count >= 2 else 'SMALL'
    opp = [0, 1, 2, 3, 4] if prediction == 'BIG' else [5, 6, 7, 8, 9]
    predicted_number = random.choice(opp)
    return {'prediction': prediction, 'predicted_number': predicted_number}

def calculate_result(prediction, predicted_number, actual_number):
    actual_size = 'BIG' if actual_number >= 5 else 'SMALL'
    win_emojis = ["😎", "🔥", "💚", "✅", "🟢", "🏆", "⚡", "💥", "👑", "🚀"]
    loss_emojis = ["😢", "❌", "🔴", "💔", "😞", "🥲", "😵", "🚫", "😬", "😓"]
    
    if actual_number == predicted_number:
        return {'status': 'JACKPOT', 'result': '🎉 JACKPOT', 'class': 'jackpot', 'size': actual_size}
    if actual_size == prediction:
        return {'status': 'WIN', 'result': 'WIN ' + random.choice(win_emojis), 'class': 'win', 'size': actual_size}
    return {'status': 'LOSS', 'result': 'LOSS ' + random.choice(loss_emojis), 'class': 'loss', 'size': actual_size}

# ==================== RESPONSE HELPER ====================
def send_response(success, message, data=None):
    return {
        'success': success,
        'message': message,
        'data': data,
        'timestamp': int(datetime.now().timestamp())
    }

# ==================== MAIN HANDLER ====================
def handle_get():
    global current_prediction, last_period, history_logs
    
    try:
        external_data = fetch_external_data()
        if not external_data:
            return send_response(False, 'Failed to fetch external data')
        
        last_entry = external_data['data']['list'][0]
        current_period = int(last_entry['issueNumber']) + 1
        history = external_data['data']['list']
        
        if last_period != current_period:
            if current_prediction and last_period:
                actual_number = int(last_entry['number'])
                result = calculate_result(
                    current_prediction['prediction'],
                    current_prediction['predicted_number'],
                    actual_number
                )
                history_logs.appendleft({
                    'period': str(last_period),
                    'prediction': current_prediction['prediction'],
                    'predicted_number': current_prediction['predicted_number'],
                    'actual_number': actual_number,
                    'actual_size': result['size'],
                    'status': result['status'],
                    'result': result['result'],
                    'class': result['class']
                })
            
            prediction_data = determine_prediction(history)
            current_prediction = {
                'period': str(current_period),
                'prediction': prediction_data['prediction'],
                'predicted_number': prediction_data['predicted_number'],
                'status': 'PENDING',
                'result': None,
                'actual_number': None,
                'actual_size': None
            }
            last_period = current_period
        
        response = current_prediction.copy()
        
        total = len(history_logs)
        wins = sum(1 for h in history_logs if h['status'] == 'WIN')
        losses = sum(1 for h in history_logs if h['status'] == 'LOSS')
        jackpots = sum(1 for h in history_logs if h['status'] == 'JACKPOT')
        win_rate = round(((wins + jackpots) / total) * 100, 2) if total > 0 else 0
        
        return send_response(True, 'Data fetched successfully', {
            'current': response,
            'history': list(history_logs),
            'stats': {
                'wins': wins,
                'losses': losses,
                'jackpots': jackpots,
                'total': total,
                'win_rate': win_rate
            },
            'external': {
                'last_number': int(last_entry['number']),
                'last_period': int(last_entry['issueNumber'])
            }
        })
        
    except Exception as e:
        return send_response(False, 'Server error: ' + str(e))

# ==================== VERCEL HANDLER ====================
def handler(request):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    if request.method != 'GET':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps(send_response(False, 'Only GET method is allowed'))
        }
    
    response = handle_get()
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }

# ==================== LOCAL RUN ====================
if __name__ == '__main__':
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import sys
    
    class LocalHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            response = handle_get()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = HTTPServer(('0.0.0.0', port), LocalHandler)
    print(f'🚀 Server running on http://localhost:{port}')
    print(f'📡 API endpoint: http://localhost:{port}/api')
    server.serve_forever()

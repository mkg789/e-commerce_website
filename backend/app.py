from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Path to database
DB_PATH = os.path.join(os.path.dirname(__file__), 'ecommerce.db')

# ---------- Routes for HTML Pages ----------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'GET':
        return render_template('checkout.html')
    elif request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        address = data.get('address')
        payment = data.get('payment')
        cart = data.get('cart')

        print("Order received:", data)  # Debug

        # Calculate total (hardcoded prices or fetched from DB if needed)
        prices = {
            'chocobar': 10.0,
            'noodels': 15.0
        }
        total = 0
        for item, qty in cart.items():
            price = prices.get(item, 0)
            total += price * qty

        # Here you could also save the order to a database

        return jsonify({'success': True, 'total': total})


@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')


# ---------- API Endpoints ----------

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Username already exists'}), 400

    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Signup successful'})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

# ---------- Run App ----------

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'ecommerce.db')

# --- Helper to get DB connection ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Home page ---
@app.route('/')
def home():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('index.html', products=products)

# --- Cart page ---
@app.route('/cart')
def cart():
    conn = get_db_connection()
    products = conn.execute("SELECT name, price FROM products").fetchall()
    conn.close()

    price_map = {row['name'].lower(): row['price'] for row in products}
    name_map = {row['name'].lower(): row['name'] for row in products}

    return render_template('cart.html', price_map=price_map, name_map=name_map)

# --- Checkout page ---
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'GET':
        conn = get_db_connection()
        products = conn.execute("SELECT name, price FROM products").fetchall()
        conn.close()

        price_map = {row['name'].lower(): row['price'] for row in products}
        name_map = {row['name'].lower(): row['name'] for row in products}

        return render_template('checkout.html', price_map=price_map, name_map=name_map)

    data = request.get_json()
    name = data.get('name')
    address = data.get('address')
    payment = data.get('payment')
    cart = data.get('cart')

    if not cart:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400

    conn = get_db_connection()
    c = conn.cursor()

    total = 0
    product_info = {}
    for product_name, qty in cart.items():
        c.execute("SELECT id, price, stock FROM products WHERE name = ? COLLATE NOCASE", (product_name,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'message': f'Product "{product_name}" not found'}), 404

        prod_id, price, available_qty = row
        if qty > available_qty:
            conn.close()
            return jsonify({'success': False, 'message': f'Not enough stock for "{product_name}". Available: {available_qty}'}), 400

        total += price * qty
        product_info[product_name] = {'id': prod_id, 'price': price, 'qty': qty, 'available_qty': available_qty}

    c.execute('''
        INSERT INTO orders (name, address, payment_method, total)
        VALUES (?, ?, ?, ?)
    ''', (name, address, payment, total))
    order_id = c.lastrowid

    for product_name, info in product_info.items():
        c.execute('''
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', (order_id, info['id'], info['qty'], info['price']))

        new_qty = info['available_qty'] - info['qty']
        c.execute('UPDATE products SET stock = ? WHERE id = ?', (new_qty, info['id']))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'total': total})

# --- Admin page ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        category = request.form.get('category')
        quantity = request.form.get('quantity')
        image = request.files.get('image')

        if not all([name, price, description, category, quantity, image]):
            conn.close()
            return "Missing fields", 400

        image_filename = None
        if image:
            image_filename = f"images/{image.filename}"
            image.save(os.path.join('static', image_filename))

        c.execute('''
            INSERT INTO products (name, price, description, image, category, stock)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, float(price), description, image_filename, category, int(quantity)))

        conn.commit()

    products = c.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('admin.html', products=products)

# --- Update product stock ---
@app.route('/admin/update_quantity/<int:product_id>', methods=['POST'])
def update_quantity(product_id):
    action = request.form.get('action')
    amount = request.form.get('amount')

    if not amount or not amount.isdigit():
        return "Invalid amount", 400

    amount = int(amount)

    conn = get_db_connection()
    c = conn.cursor()

    c.execute('SELECT stock FROM products WHERE id = ?', (product_id,))
    product = c.fetchone()
    if not product:
        conn.close()
        return "Product not found", 404

    current_qty = product['stock']

    if action == 'add':
        new_qty = current_qty + amount
    elif action == 'remove':
        new_qty = current_qty - amount
        if new_qty < 0:
            new_qty = 0
    else:
        conn.close()
        return "Invalid action", 400

    c.execute('UPDATE products SET stock = ? WHERE id = ?', (new_qty, product_id))
    conn.commit()
    conn.close()

    return redirect(url_for('admin'))

# --- Delete product ---
@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# --- Login page ---
@app.route('/login')
def login():
    return render_template('login.html')

# --- Signup page ---
@app.route('/signup')
def signup():
    return render_template('signup.html')

# --- Signup API ---
@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Username already exists'}), 400

    hashed_password = generate_password_hash(password)
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Signup successful'})

# --- Login API ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if row and check_password_hash(row['password'], password):
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

if __name__ == '__main__':
    app.run(debug=True)

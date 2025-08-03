from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('index.html', products=products)


@app.route('/cart')
def cart():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products")
    products = cursor.fetchall()
    conn.close()

    price_map = {name.lower(): price for name, price in products}
    return render_template('cart.html', price_map=price_map)


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
        username = data.get('username')  # optional, if you want to associate order with user

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Lookup user_id (optional)
        user_id = None
        if username:
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            if row:
                user_id = row[0]

        # Calculate total price from DB to avoid trusting client
        total = 0
        for product_id, qty in cart.items():
            c.execute("SELECT price FROM products WHERE name = ?", (product_id,))
            price_row = c.fetchone()
            price = price_row[0] if price_row else 0
            total += price * qty

        # Insert order
        c.execute('''
            INSERT INTO orders (user_id, name, address, payment_method, total)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, address, payment, total))
        order_id = c.lastrowid

        # Insert order items
        for product_id, qty in cart.items():
            c.execute("SELECT id, price FROM products WHERE name = ?", (product_id,))
            product = c.fetchone()
            if product:
                prod_id, price = product
                c.execute('''
                    INSERT INTO order_items (order_id, product_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                ''', (order_id, prod_id, qty, price))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'total': total})


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        image = request.files['image']

        # Ensure the image directory exists
        image_folder = os.path.join(app.root_path, 'static', 'images')
        os.makedirs(image_folder, exist_ok=True)

        # Save image to the correct location
        image_path = os.path.join(image_folder, image.filename)
        image.save(image_path)

        # Save relative path for serving via Flask static
        image_url = f'images/{image.filename}'

        cursor.execute('''
            INSERT INTO products (name, price, description, image_url)
            VALUES (?, ?, ?, ?)
        ''', (name, price, description, image_url))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    # GET: show admin page
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('admin.html', products=products)




@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Delete the product by ID
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))


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

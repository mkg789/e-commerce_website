import sqlite3

def init_db():
    conn = sqlite3.connect('ecommerce.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Optional: Create a products table (you can use this later if needed)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT
        )
    ''')

    # Example products (optional seed data)
    products = [
        ("Choco bar", 10.00, "Delicious chocolate bar"),
        ("Noodels", 15.00, "Hot instant noodles")
    ]
    try:
        cursor.executemany('INSERT INTO products (name, price, description) VALUES (?, ?, ?)', products)
    except sqlite3.IntegrityError:
        pass  # Products already added, skip

    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == '__main__':
    init_db()

from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3, os, csv
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Max 2MB

def init_db():
    conn = sqlite3.connect('database1.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY,
            name TEXT,
            purchase_price REAL,
            selling_price REAL,
            quantity INTEGER,
            image TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            quantity INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES stock(id)
        )
    ''')
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('database1.db')
    items = conn.execute("SELECT * FROM stock").fetchall()

    # Total profit from remaining stock
    total_profit = sum((item[3] - item[2]) * item[4] for item in items)

    # Today's sales
    today = datetime.now().strftime('%Y-%m-%d')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.quantity, st.purchase_price, st.selling_price
        FROM sales s
        JOIN stock st ON s.item_id = st.id
        WHERE DATE(s.timestamp) = ?
    ''', (today,))
    today_sales = cursor.fetchall()
    conn.close()

    total_items_sold_today = sum(s[0] for s in today_sales)
    profit_today = sum((s[2] - s[1]) * s[0] for s in today_sales)

    return render_template('index.html',
        items=items,
        total_profit=total_profit,
        total_items_sold_today=total_items_sold_today,
        profit_today=profit_today
    )

@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    purchase_price = float(request.form['purchase_price'])
    selling_price = float(request.form['selling_price'])
    quantity = int(request.form['quantity'])

    image_file = request.files['image']
    image_name = ''
    if image_file and image_file.filename != '':
        image_name = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
        image_file.save(image_path)

    conn = sqlite3.connect('database1.db')
    conn.execute("INSERT INTO stock (name, purchase_price, selling_price, quantity, image) VALUES (?, ?, ?, ?, ?)",
                 (name, purchase_price, selling_price, quantity, image_name))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    conn = sqlite3.connect('database1.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        purchase_price = float(request.form['purchase_price'])
        selling_price = float(request.form['selling_price'])
        quantity = int(request.form['quantity'])

        image_file = request.files['image']
        if image_file and image_file.filename != '':
            image_name = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
            image_file.save(image_path)
        else:
            image_name = request.form['current_image']

        cursor.execute('''
            UPDATE stock SET name=?, purchase_price=?, selling_price=?, quantity=?, image=? WHERE id=?
        ''', (name, purchase_price, selling_price, quantity, image_name, item_id))

        conn.commit()
        conn.close()
        return redirect('/')

    cursor.execute("SELECT * FROM stock WHERE id=?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    return render_template('edit.html', item=item)

@app.route('/delete/<int:item_id>')
def delete(item_id):
    conn = sqlite3.connect('database1.db')
    cursor = conn.cursor()
    cursor.execute("SELECT image FROM stock WHERE id=?", (item_id,))
    image = cursor.fetchone()
    if image and image[0]:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image[0]))
        except:
            pass
    cursor.execute("DELETE FROM stock WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/sell/<int:item_id>', methods=['POST'])
def sell(item_id):
    conn = sqlite3.connect('database1.db')
    cursor = conn.cursor()

    cursor.execute("SELECT quantity FROM stock WHERE id=?", (item_id,))
    result = cursor.fetchone()

    if result and result[0] > 0:
        cursor.execute("UPDATE stock SET quantity = quantity - 1 WHERE id=?", (item_id,))
        cursor.execute("INSERT INTO sales (item_id, quantity) VALUES (?, ?)", (item_id, 1))
        conn.commit()

    conn.close()
    return redirect('/')

@app.route('/download')
def download():
    conn = sqlite3.connect('database1.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock")
    items = cursor.fetchall()
    conn.close()

    from io import StringIO
    si = StringIO()
    cw = csv.writer(si)

    cw.writerow(["ID", "Name", "Purchase Price", "Selling Price", "Quantity", "Profit per Item", "Total Profit"])
    for item in items:
        id_, name, purchase_price, selling_price, quantity, image = item
        profit_per_item = selling_price - purchase_price
        total_profit = profit_per_item * quantity
        cw.writerow([id_, name, purchase_price, selling_price, quantity, profit_per_item, total_profit])

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_report.csv"}
    )

if __name__ == '__main__':
    init_db()
    if not os.path.exists('static/images'):
        os.makedirs('static/images')
    app.run(debug=True, host="0.0.0.0")

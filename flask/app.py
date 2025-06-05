from flask import Flask, render_template, request, redirect, url_for
import sqlite3, os
from werkzeug.utils import secure_filename
import csv
from flask import Response

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
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('database1.db')
    items = conn.execute("SELECT * FROM stock").fetchall()
    conn.close()
    return render_template('index.html', items=items)

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


@app.route('/download')
def download():
    conn = sqlite3.connect('database1.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock")
    items = cursor.fetchall()
    conn.close()

    # Use StringIO to create CSV in memory
    from io import StringIO
    si = StringIO()
    cw = csv.writer(si)

    # Write header
    cw.writerow(["ID", "Name", "Purchase Price", "Selling Price", "Quantity", "Profit per Item", "Total Profit"])

    # Write data rows
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
    app.run(debug=True,host="0.0.0.0")

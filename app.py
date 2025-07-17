from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Upload folder configuration
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'agri_store.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Product model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(100), nullable=False)

# Admin model
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Order model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    products = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)

# Create tables and default admin user
with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(username='admin@gmail.com').first():
        hashed_password = generate_password_hash('admin@123')
        new_admin = Admin(username='admin@gmail.com', password=hashed_password)
        db.session.add(new_admin)
        db.session.commit()

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin'] = admin.username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' in session:
        products = Product.query.all()
        orders = Order.query.all()
        return render_template('admin_dashboard.html', products=products, orders=orders)
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/change_password', methods=['GET', 'POST'])
def change_password():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    admin = Admin.query.filter_by(username=session['admin']).first()

    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if not check_password_hash(admin.password, old_password):
            flash('Old password is incorrect.', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        else:
            admin.password = generate_password_hash(new_password)
            db.session.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('admin_dashboard'))

    return render_template('change_password.html')

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        description = request.form['description']
        price = request.form['price']

        image = request.files['image']
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_product = Product(
            name=name,
            category=category,
            description=description,
            price=price,
            image_filename=filename
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.category = request.form['category']
        product.description = request.form['description']
        product.price = request.form['price']

        if 'image' in request.files and request.files['image'].filename != '':
            image = request.files['image']
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image_filename = filename

        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_product.html', product=product)

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    product = Product.query.get_or_404(product_id)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_filename)
    if os.path.exists(image_path):
        os.remove(image_path)

    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/products/<category>')
def products_by_category(category):
    products = Product.query.filter_by(category=category).all()
    return render_template('products_by_category.html', products=products, category=category)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']
    cart.append(product_id)
    session['cart'] = cart
    flash(f"{product.name} added to cart!", "success")
    return redirect(request.referrer or url_for('index'))

@app.route('/cart')
def view_cart():
    if 'cart' not in session or not session['cart']:
        flash("Your cart is empty.", "info")
        return render_template('cart.html', cart_items=[], total=0)

    cart = session['cart']
    cart_items = Product.query.filter(Product.id.in_(cart)).all()
    total = sum(item.price for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session:
        cart = session['cart']
        if product_id in cart:
            cart.remove(product_id)
            session['cart'] = cart
            flash("Item removed from cart.", "success")
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'cart' not in session or not session['cart']:
        flash("Your cart is empty.", "info")
        return redirect(url_for('view_cart'))

    cart = session['cart']
    cart_items = Product.query.filter(Product.id.in_(cart)).all()
    total = sum(item.price for item in cart_items)

    if request.method == 'POST':
        customer_name = request.form['customer_name']
        contact_number = request.form['contact_number']
        address = request.form['address']
        product_list = ', '.join([item.name for item in cart_items])

        new_order = Order(
            customer_name=customer_name,
            contact_number=contact_number,
            address=address,
            products=product_list,
            total_amount=total
        )
        db.session.add(new_order)
        db.session.commit()

        session.pop('cart', None)
        return redirect(url_for('payment_success'))

    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/payment_success')
def payment_success():
    flash("Payment successful! Your order has been placed.", "success")
    return render_template('payment_success.html')

@app.route('/admin/orders')
def view_orders():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    orders = Order.query.all()
    return render_template('view_orders.html', orders=orders)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, MenuItem, Category, Order, OrderItem, Notification
from db_functions import *
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = 'school_canteen_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

DAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница']


@app.route('/')
def index():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            if user.role == 'student':
                return redirect(url_for('student'))
            elif user.role == 'cook':
                return redirect(url_for('cook'))
            elif user.role == 'admin':
                return redirect(url_for('admin'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user(username)
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name', '')
        class_name = request.form.get('class_name', '')
        if get_user(username):
            flash('Пользователь уже существует')
        else:
            add_user(username, password, 'student', full_name, class_name)
            flash('Регистрация успешна')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/student')
def student():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    today = date.today()
    day_of_week = today.weekday()
    if day_of_week > 4:
        day_of_week = 0
    selected_day = request.args.get('day', day_of_week, type=int)
    meal_type = request.args.get('meal', 'breakfast')
    breakfast_menu = get_menu_by_day(selected_day, 'breakfast')
    lunch_menu = get_menu_by_day(selected_day, 'lunch')
    user_allergies = get_user_allergy_ids(user.id)
    breakfast_sub = get_subscription(user.id, 'breakfast')
    lunch_sub = get_subscription(user.id, 'lunch')
    orders = get_user_orders(user.id)
    unread = get_unread_notifications(user.id)

    menu_allergies = {}
    all_items = []
    for items in breakfast_menu.values():
        all_items.extend(items)
    for items in lunch_menu.values():
        all_items.extend(items)
    for item in all_items:
        item_allergies = get_menu_item_allergies(item.id)
        menu_allergies[item.id] = item_allergies

    return render_template('student.html',
                           user=user,
                           breakfast_menu=breakfast_menu,
                           lunch_menu=lunch_menu,
                           selected_day=selected_day,
                           meal_type=meal_type,
                           days=DAYS,
                           user_allergies=user_allergies,
                           menu_allergies=menu_allergies,
                           breakfast_sub=breakfast_sub,
                           lunch_sub=lunch_sub,
                           orders=orders,
                           unread_count=len(unread)
                           )


@app.route('/order', methods=['POST'])
def order():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    meal_type = request.form.get('meal_type')
    use_sub = request.form.get('use_subscription') == '1'
    item_ids = request.form.getlist('items')
    item_ids = [int(i) for i in item_ids if i]

    if not item_ids:
        flash('Выберите блюда')
        return redirect(url_for('student'))

    if use_sub:
        sub = get_subscription(user.id, meal_type)
        if not sub or sub.meals_left < 1:
            flash('Нет абонемента')
            return redirect(url_for('student'))
        use_subscription(user.id, meal_type)
        order_obj, total = create_order(user.id, meal_type, item_ids, is_subscription=True)
        add_notification(user.id, f'Заказ по абонементу оформлен. Осталось: {sub.meals_left - 1}')
    else:
        items = [MenuItem.query.get(i) for i in item_ids]
        total = sum(i.price for i in items if i)
        if user.balance < total:
            flash('Недостаточно средств')
            return redirect(url_for('student'))
        subtract_balance(user.id, total)
        add_payment(user.id, total, 'purchase')
        order_obj, _ = create_order(user.id, meal_type, item_ids, is_subscription=False)
        add_notification(user.id, f'Заказ на {total} руб. оформлен')

    flash('Заказ оформлен!')
    return redirect(url_for('student'))


@app.route('/buy_subscription', methods=['POST'])
def buy_subscription():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    meal_type = request.form.get('meal_type')
    count = int(request.form.get('count', 5))
    prices = {'breakfast': 100, 'lunch': 150}
    price = prices.get(meal_type, 100) * count

    if user.balance < price:
        flash('Недостаточно средств')
        return redirect(url_for('student'))

    subtract_balance(user.id, price)
    add_payment(user.id, price, 'subscription')
    add_subscription(user.id, meal_type, count)
    add_notification(user.id, f'Куплен абонемент на {count} приёмов ({meal_type})')
    flash(f'Абонемент на {count} приёмов куплен!')
    return redirect(url_for('student'))


@app.route('/add_balance', methods=['POST'])
def add_balance_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    amount = float(request.form.get('amount', 0))
    if amount > 0:
        add_balance(session['user_id'], amount)
        add_notification(session['user_id'], f'Баланс пополнен на {amount} руб.')
        flash(f'Баланс пополнен на {amount} руб.')
    return redirect(url_for('student'))


@app.route('/receive_order/<int:order_id>')
def receive_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if mark_order_received(order_id, session['user_id']):
        flash('Заказ получен!')
    else:
        flash('Ошибка получения заказа')
    return redirect(url_for('student'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    if request.method == 'POST':
        user.full_name = request.form.get('full_name', '')
        user.class_name = request.form.get('class_name', '')
        db.session.commit()
        flash('Профиль обновлён')
    allergies = get_all_allergies()
    user_allergies = get_user_allergy_ids(user.id)
    return render_template('profile.html', user=user, allergies=allergies, user_allergies=user_allergies)


@app.route('/toggle_allergy/<int:allergy_id>')
def toggle_allergy(allergy_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_allergies = get_user_allergy_ids(session['user_id'])
    if allergy_id in user_allergies:
        remove_user_allergy(session['user_id'], allergy_id)
    else:
        add_user_allergy(session['user_id'], allergy_id)
    return redirect(url_for('profile'))


@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    notifs = get_notifications(session['user_id'])
    mark_all_notifications_read(session['user_id'])
    user = get_user_by_id(session['user_id'])
    return render_template('notifications.html', notifications=notifs, user=user)


@app.route('/reviews')
def reviews():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    all_reviews = get_all_reviews()
    items = MenuItem.query.all()
    return render_template('reviews.html', user=user, reviews=all_reviews, items=items)


@app.route('/add_review', methods=['POST'])
def add_review_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    menu_item_id = int(request.form.get('menu_item_id'))
    text = request.form.get('text')
    rating = int(request.form.get('rating', 5))
    add_review(session['user_id'], menu_item_id, text, rating)
    flash('Отзыв добавлен!')
    return redirect(url_for('reviews'))


@app.route('/cook')
def cook():
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    orders = get_orders_to_prepare()

    items_to_cook = {}
    for order in orders:
        order_items = get_order_items(order.id)
        for oi in order_items:
            item = oi.menu_item
            if item.id not in items_to_cook:
                items_to_cook[item.id] = {'item': item, 'count': 0, 'orders': []}
            items_to_cook[item.id]['count'] += 1
            items_to_cook[item.id]['orders'].append(order.id)

    products = get_all_products()
    my_requests = PurchaseRequest.query.filter_by(created_by=user.id).order_by(PurchaseRequest.date.desc()).all()
    unread = get_unread_notifications(user.id)

    return render_template('cook.html',
                           user=user,
                           orders=orders,
                           items_to_cook=items_to_cook,
                           products=products,
                           my_requests=my_requests,
                           unread_count=len(unread)
                           )


@app.route('/prepare_order/<int:order_id>')
def prepare_order(order_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    if mark_order_prepared(order_id):
        order = Order.query.get(order_id)
        if order:
            add_notification(order.user_id, 'Ваш заказ готов! Можете получить.')
        flash('Заказ приготовлен!')
    return redirect(url_for('cook'))


@app.route('/add_request', methods=['POST'])
def add_request():
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    product_id = int(request.form.get('product_id'))
    quantity = float(request.form.get('quantity'))
    add_purchase_request(product_id, quantity, session['user_id'])
    flash('Заявка создана!')
    return redirect(url_for('cook'))


@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    stats = get_payments_stats()
    order_stats = get_orders_stats()
    expenses = get_expenses()
    pending = get_pending_requests()
    all_requests = get_all_requests()
    users = User.query.all()
    unread = get_unread_notifications(user.id)

    return render_template('admin.html',
                           user=user,
                           stats=stats,
                           order_stats=order_stats,
                           expenses=expenses,
                           pending=pending,
                           all_requests=all_requests,
                           users=users,
                           unread_count=len(unread)
                           )


@app.route('/approve/<int:req_id>')
def approve(req_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    req = PurchaseRequest.query.get(req_id)
    if req:
        approve_request(req_id)
        add_notification(req.created_by, f'Заявка на {req.product.name} одобрена!')
    return redirect(url_for('admin'))


@app.route('/reject/<int:req_id>')
def reject(req_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    req = PurchaseRequest.query.get(req_id)
    if req:
        reject_request(req_id)
        add_notification(req.created_by, f'Заявка на {req.product.name} отклонена')
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True)

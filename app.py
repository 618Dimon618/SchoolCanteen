from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, Response, jsonify
from models import db, User, MenuItem, Category, Order, OrderItem, Notification, PurchaseRequest, MenuItemIngredient, Product, Allergy, MenuItemAllergy
from db_functions import *
from datetime import date, timedelta
import random

app = Flask(__name__)

def generate_captcha():
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    return a, b, a + b
app.secret_key = 'school_canteen_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.before_request
def check_session():
    public_routes = ['login', 'register', 'static']
    if request.endpoint and request.endpoint not in public_routes:
        if 'user_id' not in session and request.endpoint != 'index':
            return redirect(url_for('login'))

DAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница']

@app.after_request
def add_no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

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
        captcha_answer = request.form.get('captcha_answer', '')
        expected = session.get('captcha_result')
        try:
            if int(captcha_answer) != expected:
                flash('Неверный ответ на проверку')
                a, b, result = generate_captcha()
                session['captcha_result'] = result
                return render_template('login.html', captcha_a=a, captcha_b=b)
        except ValueError:
            flash('Введите число')
            a, b, result = generate_captcha()
            session['captcha_result'] = result
            return render_template('login.html', captcha_a=a, captcha_b=b)
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user(username)
        if user and user.check_password(password):
            if not user.is_approved:
                flash('Ваш аккаунт ещё не подтверждён администратором')
                a, b, result = generate_captcha()
                session['captcha_result'] = result
                return render_template('login.html', captcha_a=a, captcha_b=b)
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    a, b, result = generate_captcha()
    session['captcha_result'] = result
    return render_template('login.html', captcha_a=a, captcha_b=b)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        captcha_answer = request.form.get('captcha_answer', '')
        expected = session.get('captcha_result')
        try:
            if int(captcha_answer) != expected:
                flash('Неверный ответ на проверку')
                a, b, result = generate_captcha()
                session['captcha_result'] = result
                return render_template('register.html', captcha_a=a, captcha_b=b)
        except ValueError:
            flash('Введите число')
            a, b, result = generate_captcha()
            session['captcha_result'] = result
            return render_template('register.html', captcha_a=a, captcha_b=b)
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name', '')
        class_name = request.form.get('class_name', '')
        if get_user(username):
            flash('Пользователь уже существует')
        else:
            add_user(username, password, 'student', full_name, class_name)
            admins = User.query.filter_by(role='admin').all()
            for adm in admins:
                add_notification(adm.id, f'Новая заявка на регистрацию: {full_name} ({username})')
            flash('Заявка на регистрацию отправлена. Дождитесь подтверждения администратора.')
            return redirect(url_for('login'))
    a, b, result = generate_captcha()
    session['captcha_result'] = result
    return render_template('register.html', captcha_a=a, captcha_b=b)

@app.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect(url_for('login')))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    response.delete_cookie('session')
    return response

@app.route('/student')
def student():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    breakfast_menu = get_all_unique_menu_items('breakfast')
    lunch_menu = get_all_unique_menu_items('lunch')
    user_allergies = get_user_allergy_ids(user.id)
    breakfast_sub = get_subscription(user.id, 'breakfast')
    lunch_sub = get_subscription(user.id, 'lunch')
    orders = get_user_orders(user.id)
    unread = get_unread_notifications(user.id)
    unavailable_ids = get_unavailable_item_ids()

    menu_allergies = {}
    all_items = []
    for items in breakfast_menu.values():
        all_items.extend(items)
    for items in lunch_menu.values():
        all_items.extend(items)
    for item in all_items:
        item_allergies = get_menu_item_allergies(item.id)
        menu_allergies[item.id] = item_allergies

    sub_prices = {'breakfast': 100, 'lunch': 150}

    return render_template('student.html',
        user=user,
        breakfast_menu=breakfast_menu,
        lunch_menu=lunch_menu,
        user_allergies=user_allergies,
        menu_allergies=menu_allergies,
        breakfast_sub=breakfast_sub,
        lunch_sub=lunch_sub,
        orders=orders,
        unread_count=len(unread),
        sub_prices=sub_prices,
        unavailable_ids=unavailable_ids
    )

@app.route('/order', methods=['POST'])
def order():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    meal_type = request.form.get('meal_type')
    use_sub = request.form.get('use_subscription') == '1'

    item_ids = []
    for key in request.form:
        if key.startswith('cat_'):
            val = request.form.get(key)
            if val:
                item_ids.append(int(val))

    if not item_ids:
        flash('Выберите блюда')
        return redirect(url_for('student'))

    unavailable = get_unavailable_item_ids()
    for item_id in item_ids:
        if item_id in unavailable:
            flash('Одно или несколько выбранных блюд сейчас недоступно')
            return redirect(url_for('student'))

    if use_sub:
        today = date.today()
        already_sub_orders = get_subscription_orders_count_for_day(user.id, meal_type, today)
        if already_sub_orders >= 1:
            flash('На сегодня по абонементу уже оформлен заказ для этого приёма пищи.')
            return redirect(url_for('student'))
        sub = get_subscription(user.id, meal_type)
        if not sub or sub.meals_left < 1:
            flash('Нет абонемента')
            return redirect(url_for('student'))
        use_subscription(user.id, meal_type)
        order_obj, total = create_order(user.id, meal_type, item_ids, is_subscription=True)
        prices = {'breakfast': 100, 'lunch': 150}
        sub_price = prices.get(meal_type, 100)
        add_notification(user.id, f'Заказ по абонементу оформлен ({sub_price}₽). Осталось: {sub.meals_left}')
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

    cooks = User.query.filter_by(role='cook').all()
    for c in cooks:
        add_notification(c.id, f'Новый заказ #{order_obj.id} от {user.full_name or user.username}')

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

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
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
    return render_template('review.html', user=user, reviews=all_reviews, items=items)

@app.route('/add_review', methods=['POST'])
def add_review_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    menu_item_id = int(request.form.get('menu_item_id'))
    text = request.form.get('text')
    rating = int(request.form.get('rating', 5))
    add_review(session['user_id'], menu_item_id, text, rating)
    item = MenuItem.query.get(menu_item_id)
    user = get_user_by_id(session['user_id'])
    cooks = User.query.filter_by(role='cook').all()
    for c in cooks:
        add_notification(c.id, f'Новый отзыв на "{item.name}" от {user.full_name or user.username}: {"⭐" * rating}')
    flash('Отзыв добавлен!')
    return redirect(url_for('reviews'))

@app.route('/cook')
def cook():
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    orders = get_orders_to_prepare()

    order_item_can_cook = {}
    for o in orders:
        for oi in o.items:
            if not oi.is_cooked:
                order_item_can_cook[oi.id] = check_item_ingredients_available(oi.menu_item_id)

    products = get_all_products()
    my_requests = PurchaseRequest.query.filter_by(created_by=user.id).order_by(PurchaseRequest.date.desc()).all()
    unread = get_unread_notifications(user.id)

    today = date.today()
    today_orders = Order.query.filter_by(date=today).all()
    breakfast_count = len([o for o in today_orders if o.meal_type == 'breakfast'])
    lunch_count = len([o for o in today_orders if o.meal_type == 'lunch'])
    prepared_count = len([o for o in today_orders if o.is_prepared])
    received_count = len([o for o in today_orders if o.is_received])

    return render_template('cook.html',
        user=user,
        orders=orders,
        order_item_can_cook=order_item_can_cook,
        products=products,
        my_requests=my_requests,
        unread_count=len(unread),
        breakfast_count=breakfast_count,
        lunch_count=lunch_count,
        prepared_count=prepared_count,
        received_count=received_count
    )

@app.route('/cook/dishes')
def cook_dishes():
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    unread = get_unread_notifications(user.id)

    breakfast_dishes = get_all_unique_menu_items('breakfast')
    lunch_dishes = get_all_unique_menu_items('lunch')

    dish_ingredients = {}
    dish_can_cook = {}
    all_dishes = []
    for items in breakfast_dishes.values():
        all_dishes.extend(items)
    for items in lunch_dishes.values():
        all_dishes.extend(items)
    for item in all_dishes:
        ings = MenuItemIngredient.query.filter_by(menu_item_id=item.id).all()
        dish_ingredients[item.id] = ings
        dish_can_cook[item.id] = item.is_available and check_item_ingredients_available(item.id)

    categories = Category.query.all()
    products = get_all_products()
    allergies = get_all_allergies()

    return render_template('cook_dishes.html',
        user=user,
        breakfast_dishes=breakfast_dishes,
        lunch_dishes=lunch_dishes,
        dish_ingredients=dish_ingredients,
        dish_can_cook=dish_can_cook,
        categories=categories,
        products=products,
        allergies=allergies,
        unread_count=len(unread)
    )

@app.route('/cook/toggle_item/<int:item_id>')
def toggle_item(item_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    result = toggle_menu_item_availability(item_id)
    if result is not None:
        item = MenuItem.query.get(item_id)
        status = 'доступно' if result else 'недоступно'
        flash(f'Блюдо "{item.name}" теперь {status}')
    return redirect(url_for('cook_dishes'))

@app.route('/cook/create_dish', methods=['POST'])
def create_dish():
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))

    name = request.form.get('dish_name', '').strip()
    price = request.form.get('dish_price', '0')
    category_id = request.form.get('dish_category')

    if not name or not category_id:
        flash('Укажите название и категорию')
        return redirect(url_for('cook_dishes'))

    try:
        price = float(price)
    except ValueError:
        price = 0

    category_id = int(category_id)

    ingredient_ids = request.form.getlist('ing_product[]')
    ingredient_qtys = request.form.getlist('ing_qty[]')

    ingredients_data = []
    for pid, qty in zip(ingredient_ids, ingredient_qtys):
        if pid and qty:
            try:
                ingredients_data.append((int(pid), float(qty)))
            except ValueError:
                pass

    allergy_ids = request.form.getlist('dish_allergies')
    allergy_ids = [int(a) for a in allergy_ids if a]

    item = create_custom_dish(name, price, category_id, ingredients_data, allergy_ids)
    flash(f'Блюдо "{name}" создано!')
    return redirect(url_for('cook_dishes'))

@app.route('/cook/delete_dish/<int:item_id>')
def delete_dish(item_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    item = MenuItem.query.get(item_id)
    if item:
        name = item.name
        delete_menu_item(item_id)
        flash(f'Блюдо "{name}" удалено')
    return redirect(url_for('cook_dishes'))

@app.route('/cook/cook_item/<int:oi_id>')
def cook_item(oi_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    oi = OrderItem.query.get(oi_id)
    if not oi:
        flash('Позиция не найдена')
        return redirect(url_for('cook'))
    if oi.is_cooked:
        flash('Блюдо уже приготовлено')
        return redirect(url_for('cook'))
    if mark_order_item_cooked(oi.id):
        flash(f'"{oi.menu_item.name}" приготовлено')
    else:
        flash(f'Не хватает продуктов для "{oi.menu_item.name}"')
    return redirect(url_for('cook'))

@app.route('/prepare_order/<int:order_id>')
def prepare_order(order_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    o = Order.query.get(order_id)
    if not o:
        flash('Заказ не найден')
        return redirect(url_for('cook'))
    if o.is_prepared:
        flash('Заказ уже отмечен как готовый')
        return redirect(url_for('cook'))
    if not is_order_fully_cooked(order_id):
        flash('Не все блюда в заказе приготовлены')
        return redirect(url_for('cook'))
    if mark_order_prepared(order_id):
        add_notification(o.user_id, f'Ваш заказ #{o.id} готов к выдаче!')
        flash('Заказ готов к выдаче!')
    else:
        flash('Ошибка')
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

@app.route('/cook/issued')
def cook_issued():
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    unread = get_unread_notifications(user.id)
    issued_orders = get_issued_orders()
    breakfast_issued = [o for o in issued_orders if o.meal_type == 'breakfast']
    lunch_issued = [o for o in issued_orders if o.meal_type == 'lunch']
    return render_template('cook_issued.html',
        user=user,
        unread_count=len(unread),
        issued_orders=issued_orders,
        breakfast_issued=breakfast_issued,
        lunch_issued=lunch_issued
    )

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
    pending_users = User.query.filter_by(is_approved=False).all()
    unread = get_unread_notifications(user.id)
    attendance = get_attendance_stats()

    today = date.today()
    all_today = Order.query.filter_by(date=today).all()
    breakfast_today = len([o for o in all_today if o.meal_type == 'breakfast'])
    lunch_today = len([o for o in all_today if o.meal_type == 'lunch'])
    all_orders_list = Order.query.all()
    total_breakfasts = len([o for o in all_orders_list if o.meal_type == 'breakfast'])
    total_lunches = len([o for o in all_orders_list if o.meal_type == 'lunch'])

    return render_template('admin.html',
        user=user,
        stats=stats,
        order_stats=order_stats,
        expenses=expenses,
        pending=pending,
        all_requests=all_requests,
        users=users,
        pending_users=pending_users,
        unread_count=len(unread),
        breakfast_today=breakfast_today,
        lunch_today=lunch_today,
        total_breakfasts=total_breakfasts,
        total_lunches=total_lunches,
        attendance=attendance
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

@app.route('/approve_user/<int:user_id>')
def approve_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    u = User.query.get(user_id)
    if u and not u.is_approved:
        u.is_approved = True
        db.session.commit()
        add_notification(u.id, 'Ваш аккаунт подтверждён! Теперь вы можете войти в систему.')
        flash(f'Пользователь {u.full_name or u.username} подтверждён')
    return redirect(url_for('admin'))

@app.route('/reject_user/<int:user_id>')
def reject_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    u = User.query.get(user_id)
    if u and not u.is_approved:
        db.session.delete(u)
        db.session.commit()
        flash(f'Заявка на регистрацию отклонена')
    return redirect(url_for('admin'))

@app.route('/download_report')
def download_report():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from io import BytesIO
    from datetime import datetime

    stats = get_payments_stats()
    order_stats = get_orders_stats()
    expenses = get_expenses()
    all_requests_list = get_all_requests()
    users = User.query.all()
    all_orders = Order.query.order_by(Order.created_at.desc()).all()

    wb = Workbook()
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    def style_header(ws, row, cols):
        for col in range(1, cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center')

    ws1 = wb.active
    ws1.title = 'Сводка'
    ws1.append(['Отчёт по школьной столовой'])
    ws1.merge_cells('A1:B1')
    ws1.cell(1, 1).font = Font(bold=True, size=16)
    ws1.append(['Дата формирования', datetime.now().strftime('%d.%m.%Y %H:%M')])
    ws1.append([])
    ws1.append(['Финансовые показатели'])
    ws1.cell(4, 1).font = Font(bold=True, size=14)
    ws1.append(['Показатель', 'Сумма (руб.)'])
    style_header(ws1, 5, 2)
    ws1.append(['Доход от абонементов', round(stats['subscriptions'], 2)])
    ws1.append(['Доход от покупок', round(stats['purchases'], 2)])
    ws1.append(['Общий доход', round(stats['total_income'], 2)])
    ws1.append(['Расходы на закупки', round(expenses, 2)])
    ws1.append(['Чистая прибыль', round(stats['total_income'] - expenses, 2)])
    ws1.append([])
    ws1.append(['Статистика заказов'])
    ws1.cell(ws1.max_row, 1).font = Font(bold=True, size=14)
    ws1.append(['Показатель', 'Значение'])
    style_header(ws1, ws1.max_row, 2)
    ws1.append(['Всего заказов', order_stats['total']])
    ws1.append(['Заказов за сегодня', order_stats['today']])
    ws1.append(['Получено', order_stats['received']])
    breakfast_total = len([o for o in all_orders if o.meal_type == 'breakfast'])
    lunch_total = len([o for o in all_orders if o.meal_type == 'lunch'])
    ws1.append(['Всего завтраков', breakfast_total])
    ws1.append(['Всего обедов', lunch_total])
    ws1.column_dimensions['A'].width = 30
    ws1.column_dimensions['B'].width = 20

    ws2 = wb.create_sheet('Учёт завтраков')
    breakfast_orders = [o for o in all_orders if o.meal_type == 'breakfast']
    ws2.append(['Учёт завтраков'])
    ws2.merge_cells('A1:G1')
    ws2.cell(1, 1).font = Font(bold=True, size=14)
    ws2.append(['Всего завтраков:', len(breakfast_orders)])
    ws2.append([])
    ws2.append(['№', 'Дата', 'Ученик', 'Класс', 'Блюда', 'Оплата', 'Статус'])
    style_header(ws2, 4, 7)
    for o in breakfast_orders:
        items_str = ', '.join([oi.menu_item.name for oi in o.items])
        payment = 'Абонемент' if o.is_subscription else 'Разовая'
        status = 'Получен' if o.is_received else ('Готов' if o.is_prepared else 'Готовится')
        ws2.append([o.id, o.date.strftime('%d.%m.%Y'), o.user.full_name or o.user.username, o.user.class_name or '-', items_str, payment, status])
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        ws2.column_dimensions[col].width = 18
    ws2.column_dimensions['E'].width = 40

    ws3 = wb.create_sheet('Учёт обедов')
    lunch_orders = [o for o in all_orders if o.meal_type == 'lunch']
    ws3.append(['Учёт обедов'])
    ws3.merge_cells('A1:G1')
    ws3.cell(1, 1).font = Font(bold=True, size=14)
    ws3.append(['Всего обедов:', len(lunch_orders)])
    ws3.append([])
    ws3.append(['№', 'Дата', 'Ученик', 'Класс', 'Блюда', 'Оплата', 'Статус'])
    style_header(ws3, 4, 7)
    for o in lunch_orders:
        items_str = ', '.join([oi.menu_item.name for oi in o.items])
        payment = 'Абонемент' if o.is_subscription else 'Разовая'
        status = 'Получен' if o.is_received else ('Готов' if o.is_prepared else 'Готовится')
        ws3.append([o.id, o.date.strftime('%d.%m.%Y'), o.user.full_name or o.user.username, o.user.class_name or '-', items_str, payment, status])
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        ws3.column_dimensions[col].width = 18
    ws3.column_dimensions['E'].width = 40

    ws4 = wb.create_sheet('Все заказы')
    ws4.append(['Все заказы'])
    ws4.merge_cells('A1:H1')
    ws4.cell(1, 1).font = Font(bold=True, size=14)
    ws4.append([])
    ws4.append(['№', 'Дата', 'Ученик', 'Класс', 'Приём пищи', 'Блюда', 'Оплата', 'Статус'])
    style_header(ws4, 3, 8)
    for o in all_orders:
        items_str = ', '.join([oi.menu_item.name for oi in o.items])
        meal = 'Завтрак' if o.meal_type == 'breakfast' else 'Обед'
        payment = 'Абонемент' if o.is_subscription else 'Разовая'
        status = 'Получен' if o.is_received else ('Готов' if o.is_prepared else 'Готовится')
        ws4.append([o.id, o.date.strftime('%d.%m.%Y'), o.user.full_name or o.user.username, o.user.class_name or '-', meal, items_str, payment, status])
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
        ws4.column_dimensions[col].width = 18
    ws4.column_dimensions['F'].width = 40

    ws5 = wb.create_sheet('Заявки на закупку')
    ws5.append(['Заявки на закупку'])
    ws5.merge_cells('A1:F1')
    ws5.cell(1, 1).font = Font(bold=True, size=14)
    ws5.append([])
    ws5.append(['Дата', 'Продукт', 'Количество', 'Ед.', 'Сумма (руб.)', 'Статус'])
    style_header(ws5, 3, 6)
    status_map = {'pending': 'Ожидает', 'approved': 'Одобрена', 'rejected': 'Отклонена'}
    for req in all_requests_list:
        ws5.append([req.date.strftime('%d.%m.%Y'), req.product.name, req.quantity, req.product.unit, round(req.quantity * req.product.price, 2), status_map.get(req.status, req.status)])
    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
        ws5.column_dimensions[col].width = 18

    ws6 = wb.create_sheet('Пользователи')
    ws6.append(['Пользователи'])
    ws6.merge_cells('A1:G1')
    ws6.cell(1, 1).font = Font(bold=True, size=14)
    ws6.append([])
    ws6.append(['ID', 'Логин', 'ФИО', 'Класс', 'Роль', 'Баланс (руб.)', 'Статус'])
    style_header(ws6, 3, 7)
    role_map = {'student': 'Ученик', 'cook': 'Повар', 'admin': 'Администратор'}
    for u in users:
        ws6.append([u.id, u.username, u.full_name or '-', u.class_name or '-', role_map.get(u.role, u.role), round(u.balance, 2), 'Подтверждён' if u.is_approved else 'Ожидает'])
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        ws6.column_dimensions[col].width = 18

    ws7 = wb.create_sheet('Продукты')
    ws7.append(['Продукты'])
    ws7.merge_cells('A1:E1')
    ws7.cell(1, 1).font = Font(bold=True, size=14)
    ws7.append([])
    ws7.append(['ID продукта', 'Название', 'Остаток', 'Ед. измерения', 'Цена за ед. (руб.)'])
    style_header(ws7, 3, 5)
    all_products = Product.query.order_by(Product.id).all()
    for p in all_products:
        ws7.append([p.id, p.name, round(p.quantity, 2), p.unit, round(p.price, 2)])
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws7.column_dimensions[col].width = 22

    ws8 = wb.create_sheet('Приготовленные блюда')
    ws8.append(['Приготовленные блюда'])
    ws8.merge_cells('A1:H1')
    ws8.cell(1, 1).font = Font(bold=True, size=14)
    ws8.append([])
    ws8.append(['ID позиции', 'ID заказа', 'ID блюда', 'Блюдо', 'Приготовлено', 'ID ученика', 'Ученик', 'Цена (руб.)'])
    style_header(ws8, 3, 8)
    all_oi = OrderItem.query.order_by(OrderItem.order_id).all()
    for oi in all_oi:
        o = Order.query.get(oi.order_id)
        ws8.append([
            oi.id, oi.order_id, oi.menu_item_id, oi.menu_item.name,
            'Да' if oi.is_cooked else 'Нет',
            o.user_id if o else '-',
            (o.user.full_name or o.user.username) if o else '-',
            round(oi.price, 2)
        ])
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
        ws8.column_dimensions[col].width = 20

    ws9 = wb.create_sheet('Блюда и ингредиенты')
    ws9.append(['Связь блюд и продуктов'])
    ws9.merge_cells('A1:F1')
    ws9.cell(1, 1).font = Font(bold=True, size=14)
    ws9.append([])
    ws9.append(['ID блюда', 'Блюдо', 'ID продукта', 'Продукт', 'Кол-во на порцию', 'Ед.'])
    style_header(ws9, 3, 6)
    all_menu_items = MenuItem.query.order_by(MenuItem.id).all()
    seen = set()
    for mi in all_menu_items:
        key = mi.name
        if key in seen:
            continue
        seen.add(key)
        ings = MenuItemIngredient.query.filter_by(menu_item_id=mi.id).all()
        if ings:
            for ing in ings:
                ws9.append([mi.id, mi.name, ing.product_id, ing.product.name, round(ing.quantity, 4), ing.product.unit])
        else:
            ws9.append([mi.id, mi.name, '-', '-', '-', '-'])
    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
        ws9.column_dimensions[col].width = 22

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=report.xlsx'}
    )

# ===================== API ROUTES =====================

@app.route('/api/order', methods=['POST'])
def api_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Не авторизован'})
    user = get_user_by_id(session['user_id'])
    meal_type = request.form.get('meal_type')
    use_sub = request.form.get('use_subscription') == '1'

    item_ids = []
    for key in request.form:
        if key.startswith('cat_'):
            val = request.form.get(key)
            if val:
                item_ids.append(int(val))

    if not item_ids:
        return jsonify({'success': False, 'message': 'Выберите блюда'})

    unavailable = get_unavailable_item_ids()
    for item_id in item_ids:
        if item_id in unavailable:
            return jsonify({'success': False, 'message': 'Одно или несколько блюд недоступно'})

    if use_sub:
        today = date.today()
        already = get_subscription_orders_count_for_day(user.id, meal_type, today)
        if already >= 1:
            return jsonify({'success': False, 'message': 'По абонементу уже оформлен заказ'})
        sub = get_subscription(user.id, meal_type)
        if not sub or sub.meals_left < 1:
            return jsonify({'success': False, 'message': 'Нет абонемента'})
        use_subscription(user.id, meal_type)
        order_obj, total = create_order(user.id, meal_type, item_ids, is_subscription=True)
        cooks = User.query.filter_by(role='cook').all()
        for c in cooks:
            add_notification(c.id, f'Новый заказ #{order_obj.id} от {user.full_name or user.username}')
        return jsonify({
            'success': True,
            'message': 'Заказ по абонементу оформлен!',
            'balance': user.balance,
            'sub_left': sub.meals_left
        })
    else:
        items = [MenuItem.query.get(i) for i in item_ids]
        total = sum(i.price for i in items if i)
        if user.balance < total:
            return jsonify({'success': False, 'message': 'Недостаточно средств'})
        subtract_balance(user.id, total)
        add_payment(user.id, total, 'purchase')
        order_obj, _ = create_order(user.id, meal_type, item_ids, is_subscription=False)
        cooks = User.query.filter_by(role='cook').all()
        for c in cooks:
            add_notification(c.id, f'Новый заказ #{order_obj.id} от {user.full_name or user.username}')
        user = get_user_by_id(session['user_id'])
        return jsonify({
            'success': True,
            'message': f'Заказ на {total} руб. оформлен!',
            'balance': user.balance
        })

@app.route('/api/add_balance', methods=['POST'])
def api_add_balance():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Не авторизован'})
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Неверная сумма'})
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Сумма должна быть больше 0'})
    add_balance(session['user_id'], amount)
    user = get_user_by_id(session['user_id'])
    return jsonify({
        'success': True,
        'message': f'Баланс пополнен на {amount} руб.',
        'balance': user.balance
    })

@app.route('/api/prepare_order/<int:order_id>', methods=['POST'])
def api_prepare_order(order_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return jsonify({'success': False, 'message': 'Нет доступа'})
    o = Order.query.get(order_id)
    if not o:
        return jsonify({'success': False, 'message': 'Заказ не найден'})
    if o.is_prepared:
        return jsonify({'success': False, 'message': 'Уже готов'})
    if not is_order_fully_cooked(order_id):
        return jsonify({'success': False, 'message': 'Не все блюда приготовлены'})
    if mark_order_prepared(order_id):
        add_notification(o.user_id, f'Ваш заказ #{o.id} готов к выдаче!')
        return jsonify({'success': True, 'message': 'Заказ готов к выдаче!'})
    return jsonify({'success': False, 'message': 'Ошибка'})

@app.route('/api/cook_item/<int:oi_id>', methods=['POST'])
def api_cook_item(oi_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return jsonify({'success': False, 'message': 'Нет доступа'})
    oi = OrderItem.query.get(oi_id)
    if not oi:
        return jsonify({'success': False, 'message': 'Не найдено'})
    if oi.is_cooked:
        return jsonify({'success': False, 'message': 'Уже приготовлено'})
    if mark_order_item_cooked(oi.id):
        order_ready = is_order_fully_cooked(oi.order_id)
        return jsonify({
            'success': True,
            'message': f'{oi.menu_item.name} приготовлено',
            'order_ready': order_ready
        })
    return jsonify({'success': False, 'message': 'Не хватает продуктов'})

@app.route('/api/toggle_item/<int:item_id>', methods=['POST'])
def api_toggle_item(item_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return jsonify({'success': False, 'message': 'Нет доступа'})
    result = toggle_menu_item_availability(item_id)
    if result is not None:
        item = MenuItem.query.get(item_id)
        status = 'доступно' if result else 'недоступно'
        return jsonify({
            'success': True,
            'message': f'{item.name} теперь {status}',
            'is_available': result
        })
    return jsonify({'success': False, 'message': 'Ошибка'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

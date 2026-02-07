from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, Response
from models import db, User, MenuItem, Category, Order, OrderItem, Notification, PurchaseRequest, MenuItemIngredient
from db_functions import *
from datetime import date, timedelta

app = Flask(__name__)
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
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user(username)
        if user and user.check_password(password):
            if not user.is_approved:
                flash('Ваш аккаунт ещё не подтверждён администратором')
                return render_template('login.html')
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
            admins = User.query.filter_by(role='admin').all()
            for a in admins:
                add_notification(a.id, f'Новая заявка на регистрацию: {full_name} ({username})')
            flash('Заявка на регистрацию отправлена. Дождитесь подтверждения администратора.')
            return redirect(url_for('login'))
    return render_template('register.html')

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

    sub_prices = {'breakfast': 100, 'lunch': 150}

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
        unread_count=len(unread),
        sub_prices=sub_prices
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

    if use_sub:
        from db_functions import get_subscription_orders_count_for_day
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

    order_ingredients = {}
    for o in orders:
        for oi in o.items:
            if oi.menu_item.id not in order_ingredients:
                ings = MenuItemIngredient.query.filter_by(menu_item_id=oi.menu_item.id).all()
                order_ingredients[oi.menu_item.id] = ings

    products = get_all_products()
    my_requests = PurchaseRequest.query.filter_by(created_by=user.id).order_by(PurchaseRequest.date.desc()).all()
    unread = get_unread_notifications(user.id)

    return render_template('cook.html',
        user=user,
        orders=orders,
        order_ingredients=order_ingredients,
        products=products,
        my_requests=my_requests,
        unread_count=len(unread)
    )

@app.route('/prepare_order/<int:order_id>')
def prepare_order(order_id):
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))
    o = Order.query.get(order_id)
    if o and not o.is_prepared:
        if mark_order_prepared(order_id):
            add_notification(o.user_id, f'Ваш заказ #{o.id} готов к выдаче! Можете получить.')
            flash('Заказ готов к выдаче!')
        else:
            flash('Ошибка при подготовке заказа')
    else:
        flash('Заказ уже приготовлен или не найден')
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
    pending_users = User.query.filter_by(is_approved=False).all()
    unread = get_unread_notifications(user.id)

    return render_template('admin.html',
        user=user,
        stats=stats,
        order_stats=order_stats,
        expenses=expenses,
        pending=pending,
        all_requests=all_requests,
        users=users,
        pending_users=pending_users,
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

    from io import StringIO
    import csv
    from datetime import datetime

    stats = get_payments_stats()
    order_stats = get_orders_stats()
    expenses = get_expenses()
    all_requests_list = get_all_requests()
    users = User.query.all()
    all_orders = Order.query.order_by(Order.created_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output, delimiter=';')

    writer.writerow(['Отчёт по школьной столовой'])
    writer.writerow(['Дата формирования', datetime.now().strftime('%d.%m.%Y %H:%M')])
    writer.writerow([])

    writer.writerow(['Финансы'])
    writer.writerow(['Показатель', 'Сумма (руб.)'])
    writer.writerow(['Доход от абонементов', f'{stats["subscriptions"]:.2f}'])
    writer.writerow(['Доход от покупок', f'{stats["purchases"]:.2f}'])
    writer.writerow(['Общий доход', f'{stats["total_income"]:.2f}'])
    writer.writerow(['Расходы на закупки', f'{expenses:.2f}'])
    writer.writerow(['Чистая прибыль', f'{stats["total_income"] - expenses:.2f}'])
    writer.writerow([])

    writer.writerow(['Статистика заказов'])
    writer.writerow(['Показатель', 'Значение'])
    writer.writerow(['Всего заказов', order_stats['total']])
    writer.writerow(['Заказов за сегодня', order_stats['today']])
    writer.writerow(['Получено', order_stats['received']])
    writer.writerow([])

    writer.writerow(['Заказы'])
    writer.writerow(['№', 'Дата', 'Ученик', 'Приём пищи', 'Оплата', 'Блюда', 'Статус'])
    for o in all_orders:
        items_str = ', '.join([oi.menu_item.name for oi in o.items])
        meal = 'Завтрак' if o.meal_type == 'breakfast' else 'Обед'
        payment = 'Абонемент' if o.is_subscription else 'Разовая'
        if o.is_received:
            status = 'Получен'
        elif o.is_prepared:
            status = 'Готов'
        else:
            status = 'Готовится'
        writer.writerow([o.id, o.date.strftime('%d.%m.%Y'), o.user.full_name or o.user.username, meal, payment, items_str, status])
    writer.writerow([])

    writer.writerow(['Заявки на закупку'])
    writer.writerow(['Дата', 'Продукт', 'Количество', 'Ед.', 'Сумма (руб.)', 'Статус'])
    for req in all_requests_list:
        status_map = {'pending': 'Ожидает', 'approved': 'Одобрена', 'rejected': 'Отклонена'}
        writer.writerow([
            req.date.strftime('%d.%m.%Y'),
            req.product.name,
            req.quantity,
            req.product.unit,
            f'{req.quantity * req.product.price:.2f}',
            status_map.get(req.status, req.status)
        ])
    writer.writerow([])

    writer.writerow(['Пользователи'])
    writer.writerow(['ID', 'Логин', 'ФИО', 'Класс', 'Роль', 'Баланс (руб.)', 'Статус'])
    for u in users:
        role_map = {'student': 'Ученик', 'cook': 'Повар', 'admin': 'Администратор'}
        writer.writerow([
            u.id,
            u.username,
            u.full_name or '-',
            u.class_name or '-',
            role_map.get(u.role, u.role),
            f'{u.balance:.2f}',
            'Подтверждён' if u.is_approved else 'Ожидает'
        ])

    content = output.getvalue()
    output.close()

    return Response(
        '\ufeff' + content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=report.csv'}
    )
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
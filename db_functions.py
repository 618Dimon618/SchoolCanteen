from models import db, User, Allergy, UserAllergy, Category, MenuItem, MenuItemAllergy
from models import Product, MenuItemIngredient, Subscription, Order, OrderItem
from models import Payment, Review, PurchaseRequest, Notification
from datetime import datetime, date


def add_user(username, password, role, full_name='', class_name=''):
    user = User(username=username, role=role, full_name=full_name, class_name=class_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def get_user(username):
    return User.query.filter_by(username=username).first()


def get_user_by_id(user_id):
    return User.query.get(user_id)


def add_allergy(name):
    allergy = Allergy(name=name)
    db.session.add(allergy)
    db.session.commit()
    return allergy


def get_all_allergies():
    return Allergy.query.all()


def add_user_allergy(user_id, allergy_id):
    exists = UserAllergy.query.filter_by(user_id=user_id, allergy_id=allergy_id).first()
    if not exists:
        ua = UserAllergy(user_id=user_id, allergy_id=allergy_id)
        db.session.add(ua)
        db.session.commit()


def remove_user_allergy(user_id, allergy_id):
    ua = UserAllergy.query.filter_by(user_id=user_id, allergy_id=allergy_id).first()
    if ua:
        db.session.delete(ua)
        db.session.commit()


def get_user_allergies(user_id):
    uas = UserAllergy.query.filter_by(user_id=user_id).all()
    return [Allergy.query.get(ua.allergy_id) for ua in uas]


def get_user_allergy_ids(user_id):
    uas = UserAllergy.query.filter_by(user_id=user_id).all()
    return [ua.allergy_id for ua in uas]


def add_category(name, meal_type):
    cat = Category(name=name, meal_type=meal_type)
    db.session.add(cat)
    db.session.commit()
    return cat


def get_categories_by_meal(meal_type):
    return Category.query.filter_by(meal_type=meal_type).all()


def add_menu_item(name, price, category_id, day_of_week):
    item = MenuItem(name=name, price=price, category_id=category_id, day_of_week=day_of_week)
    db.session.add(item)
    db.session.commit()
    return item


def add_menu_item_allergy(menu_item_id, allergy_id):
    mia = MenuItemAllergy(menu_item_id=menu_item_id, allergy_id=allergy_id)
    db.session.add(mia)
    db.session.commit()


def get_menu_item_allergies(menu_item_id):
    mias = MenuItemAllergy.query.filter_by(menu_item_id=menu_item_id).all()
    return [mia.allergy for mia in mias]


def get_menu_by_day(day_of_week, meal_type):
    categories = Category.query.filter_by(meal_type=meal_type).all()
    result = {}
    for cat in categories:
        items = MenuItem.query.filter_by(category_id=cat.id, day_of_week=day_of_week).all()
        if items:
            result[cat] = items
    return result


def add_product(name, quantity, unit, price=0):
    prod = Product(name=name, quantity=quantity, unit=unit, price=price)
    db.session.add(prod)
    db.session.commit()
    return prod


def get_all_products():
    return Product.query.all()


def update_product_quantity(product_id, quantity):
    prod = Product.query.get(product_id)
    if prod:
        prod.quantity = quantity
        db.session.commit()


def add_ingredient(menu_item_id, product_id, quantity):
    ing = MenuItemIngredient(menu_item_id=menu_item_id, product_id=product_id, quantity=quantity)
    db.session.add(ing)
    db.session.commit()


def get_subscription(user_id, meal_type):
    return Subscription.query.filter_by(user_id=user_id, meal_type=meal_type).first()


def add_subscription(user_id, meal_type, meals):
    sub = get_subscription(user_id, meal_type)
    if sub:
        sub.meals_left += meals
    else:
        sub = Subscription(user_id=user_id, meal_type=meal_type, meals_left=meals)
        db.session.add(sub)
    db.session.commit()
    return sub


def use_subscription(user_id, meal_type):
    sub = get_subscription(user_id, meal_type)
    if sub and sub.meals_left > 0:
        sub.meals_left -= 1
        db.session.commit()
        return True
    return False


def create_order(user_id, meal_type, item_ids, is_subscription=False):
    today = date.today()
    order = Order(user_id=user_id, date=today, meal_type=meal_type, is_subscription=is_subscription)
    db.session.add(order)
    db.session.commit()

    total = 0
    for item_id in item_ids:
        item = MenuItem.query.get(item_id)
        if item:
            oi = OrderItem(order_id=order.id, menu_item_id=item_id, price=item.price)
            db.session.add(oi)
            total += item.price
    db.session.commit()
    return order, total


def get_user_orders(user_id):
    return Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()


def get_order_items(order_id):
    return OrderItem.query.filter_by(order_id=order_id).all()


def get_today_orders():
    today = date.today()
    return Order.query.filter_by(date=today).all()


def get_orders_to_prepare():
    today = date.today()
    return Order.query.filter_by(date=today, is_prepared=False).all()


def mark_order_prepared(order_id):
    order = Order.query.get(order_id)
    if order and not order.is_prepared:
        order.is_prepared = True
        items = OrderItem.query.filter_by(order_id=order_id).all()
        for oi in items:
            ingredients = MenuItemIngredient.query.filter_by(menu_item_id=oi.menu_item_id).all()
            for ing in ingredients:
                prod = Product.query.get(ing.product_id)
                if prod:
                    prod.quantity = round(max(0, prod.quantity - ing.quantity), 2)
        db.session.commit()
        return True
    return False


def mark_order_received(order_id, user_id):
    order = Order.query.get(order_id)
    if order and order.user_id == user_id and order.is_prepared and not order.is_received:
        order.is_received = True
        db.session.commit()
        return True
    return False


def add_payment(user_id, amount, payment_type):
    payment = Payment(user_id=user_id, amount=amount, payment_type=payment_type)
    db.session.add(payment)
    db.session.commit()
    return payment


def add_balance(user_id, amount):
    user = User.query.get(user_id)
    if user:
        user.balance += amount
        add_payment(user_id, amount, 'deposit')
        db.session.commit()
        return True
    return False


def subtract_balance(user_id, amount):
    user = User.query.get(user_id)
    if user and user.balance >= amount:
        user.balance -= amount
        db.session.commit()
        return True
    return False


def add_review(user_id, menu_item_id, text, rating):
    review = Review(user_id=user_id, menu_item_id=menu_item_id, text=text, rating=rating)
    db.session.add(review)
    db.session.commit()
    return review


def get_reviews(menu_item_id):
    return Review.query.filter_by(menu_item_id=menu_item_id).order_by(Review.date.desc()).all()


def get_all_reviews():
    return Review.query.order_by(Review.date.desc()).all()


def add_purchase_request(product_id, quantity, user_id):
    req = PurchaseRequest(product_id=product_id, quantity=quantity, created_by=user_id)
    db.session.add(req)
    db.session.commit()
    return req


def get_pending_requests():
    return PurchaseRequest.query.filter_by(status='pending').all()


def get_all_requests():
    return PurchaseRequest.query.order_by(PurchaseRequest.date.desc()).all()


def approve_request(request_id):
    req = PurchaseRequest.query.get(request_id)
    if req:
        req.status = 'approved'
        prod = Product.query.get(req.product_id)
        if prod:
            prod.quantity += req.quantity
        db.session.commit()
        return True
    return False


def reject_request(request_id):
    req = PurchaseRequest.query.get(request_id)
    if req:
        req.status = 'rejected'
        db.session.commit()
        return True
    return False


def add_notification(user_id, text):
    notif = Notification(user_id=user_id, text=text)
    db.session.add(notif)
    db.session.commit()
    return notif


def get_notifications(user_id):
    return Notification.query.filter_by(user_id=user_id).order_by(Notification.date.desc()).all()


def get_unread_notifications(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).all()


def mark_notification_read(notif_id):
    notif = Notification.query.get(notif_id)
    if notif:
        notif.is_read = True
        db.session.commit()


def mark_all_notifications_read(user_id):
    notifs = Notification.query.filter_by(user_id=user_id, is_read=False).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()


def get_payments_stats():
    deposits = Payment.query.filter_by(payment_type='deposit').all()
    subscriptions = Payment.query.filter_by(payment_type='subscription').all()
    purchases = Payment.query.filter_by(payment_type='purchase').all()
    return {
        'deposits': sum(p.amount for p in deposits),
        'subscriptions': sum(p.amount for p in subscriptions),
        'purchases': sum(p.amount for p in purchases),
        'total_income': sum(p.amount for p in subscriptions) + sum(p.amount for p in purchases)
    }


def get_orders_stats():
    today = date.today()
    all_orders = Order.query.all()
    today_orders = Order.query.filter_by(date=today).all()
    return {
        'total': len(all_orders),
        'today': len(today_orders),
        'received': len([o for o in all_orders if o.is_received])
    }


def get_expenses():
    approved = PurchaseRequest.query.filter_by(status='approved').all()
    total = 0
    for req in approved:
        prod = Product.query.get(req.product_id)
        if prod:
            total += req.quantity * prod.price
    return total


def get_subscription_orders_count_for_day(user_id, meal_type, day=None):
    """Сколько заказов по абонементу у пользователя за указанный день и тип приёма пищи."""
    if day is None:
        day = date.today()
    return Order.query.filter_by(
        user_id=user_id,
        date=day,
        meal_type=meal_type,
        is_subscription=True
    ).count()

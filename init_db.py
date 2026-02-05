import os
from flask import Flask
from models import db, User, Allergy, Category, MenuItem, MenuItemAllergy, Product, MenuItemIngredient
from db_functions import add_user, add_allergy, add_category, add_menu_item, add_product, add_menu_item_allergy, \
    add_ingredient

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

if os.path.exists('instance/canteen.db'):
    os.remove('instance/canteen.db')

with app.app_context():
    db.create_all()

    admin = add_user('admin', 'admin123', 'admin', 'Администратор', '')
    cook = add_user('cook', 'cook123', 'cook', 'Повар Иванов', '')
    student = add_user('student1', 'student123', 'student', 'Петров Иван', '9А')

    milk = add_allergy('Молоко')
    gluten = add_allergy('Глютен')
    eggs = add_allergy('Яйца')
    nuts = add_allergy('Орехи')
    fish = add_allergy('Рыба')
    citrus = add_allergy('Цитрусовые')

    b_main = add_category('Основное блюдо', 'breakfast')
    b_fruit = add_category('Фрукты', 'breakfast')
    b_drink = add_category('Напиток', 'breakfast')

    l_soup = add_category('Суп', 'lunch')
    l_main = add_category('Горячее', 'lunch')
    l_salad = add_category('Салат', 'lunch')
    l_drink = add_category('Напиток', 'lunch')

    breakfast_menu = {
        0: {
            b_main.id: [('Каша овсяная', 60), ('Омлет', 80)],
            b_fruit.id: [('Яблоко', 30), ('Банан', 35)],
            b_drink.id: [('Чай', 20), ('Какао', 35)]
        },
        1: {
            b_main.id: [('Каша рисовая', 55), ('Сырники', 90)],
            b_fruit.id: [('Груша', 35), ('Апельсин', 40)],
            b_drink.id: [('Компот', 25), ('Молоко', 30)]
        },
        2: {
            b_main.id: [('Каша гречневая', 50), ('Блины', 85)],
            b_fruit.id: [('Яблоко', 30), ('Мандарин', 35)],
            b_drink.id: [('Чай', 20), ('Сок яблочный', 40)]
        },
        3: {
            b_main.id: [('Каша пшенная', 55), ('Оладьи', 75)],
            b_fruit.id: [('Банан', 35), ('Киви', 45)],
            b_drink.id: [('Какао', 35), ('Компот', 25)]
        },
        4: {
            b_main.id: [('Каша манная', 50), ('Творожная запеканка', 95)],
            b_fruit.id: [('Груша', 35), ('Яблоко', 30)],
            b_drink.id: [('Чай', 20), ('Молоко', 30)]
        }
    }

    lunch_menu = {
        0: {
            l_soup.id: [('Борщ', 70), ('Куриный суп', 65)],
            l_main.id: [('Котлета с пюре', 120), ('Гуляш с гречкой', 130)],
            l_salad.id: [('Салат витаминный', 45), ('Салат из капусты', 40)],
            l_drink.id: [('Компот', 25), ('Чай', 20)]
        },
        1: {
            l_soup.id: [('Щи', 65), ('Рассольник', 70)],
            l_main.id: [('Рыба с рисом', 140), ('Тефтели с макаронами', 115)],
            l_salad.id: [('Салат огурцы-помидоры', 50), ('Винегрет', 45)],
            l_drink.id: [('Сок', 40), ('Компот', 25)]
        },
        2: {
            l_soup.id: [('Гороховый суп', 60), ('Суп-лапша', 65)],
            l_main.id: [('Курица с картофелем', 135), ('Печень с гречкой', 125)],
            l_salad.id: [('Салат морковный', 35), ('Салат свекольный', 40)],
            l_drink.id: [('Чай', 20), ('Кисель', 30)]
        },
        3: {
            l_soup.id: [('Суп фасолевый', 65), ('Борщ', 70)],
            l_main.id: [('Биточки с пюре', 110), ('Плов', 120)],
            l_salad.id: [('Салат из редиса', 40), ('Салат греческий', 55)],
            l_drink.id: [('Компот', 25), ('Морс', 30)]
        },
        4: {
            l_soup.id: [('Уха', 75), ('Суп овощной', 55)],
            l_main.id: [('Жаркое', 140), ('Запеканка мясная', 125)],
            l_salad.id: [('Салат оливье', 60), ('Салат витаминный', 45)],
            l_drink.id: [('Чай', 20), ('Сок', 40)]
        }
    }

    item_allergies = {
        'Каша овсяная': [milk.id, gluten.id],
        'Каша рисовая': [milk.id],
        'Каша гречневая': [milk.id],
        'Каша пшенная': [milk.id],
        'Каша манная': [milk.id, gluten.id],
        'Омлет': [eggs.id, milk.id],
        'Сырники': [eggs.id, milk.id, gluten.id],
        'Блины': [eggs.id, milk.id, gluten.id],
        'Оладьи': [eggs.id, milk.id, gluten.id],
        'Творожная запеканка': [eggs.id, milk.id],
        'Какао': [milk.id],
        'Молоко': [milk.id],
        'Апельсин': [citrus.id],
        'Мандарин': [citrus.id],
        'Рыба с рисом': [fish.id],
        'Уха': [fish.id],
        'Котлета с пюре': [gluten.id, eggs.id],
        'Тефтели с макаронами': [gluten.id, eggs.id],
        'Биточки с пюре': [gluten.id, eggs.id],
        'Салат оливье': [eggs.id],
    }

    for day, categories in breakfast_menu.items():
        for cat_id, items in categories.items():
            for name, price in items:
                item = add_menu_item(name, price, cat_id, day)
                if name in item_allergies:
                    for allergy_id in item_allergies[name]:
                        add_menu_item_allergy(item.id, allergy_id)

    for day, categories in lunch_menu.items():
        for cat_id, items in categories.items():
            for name, price in items:
                item = add_menu_item(name, price, cat_id, day)
                if name in item_allergies:
                    for allergy_id in item_allergies[name]:
                        add_menu_item_allergy(item.id, allergy_id)

    add_product('Молоко', 50, 'л', 80)
    add_product('Мука', 30, 'кг', 60)
    add_product('Яйца', 100, 'шт', 10)
    add_product('Масло сливочное', 20, 'кг', 600)
    add_product('Сахар', 25, 'кг', 70)
    add_product('Соль', 10, 'кг', 30)
    add_product('Крупа овсяная', 15, 'кг', 90)
    add_product('Крупа гречневая', 20, 'кг', 120)
    add_product('Крупа рисовая', 20, 'кг', 100)
    add_product('Мясо говядина', 30, 'кг', 450)
    add_product('Мясо курица', 40, 'кг', 280)
    add_product('Рыба', 25, 'кг', 350)
    add_product('Картофель', 100, 'кг', 40)
    add_product('Капуста', 50, 'кг', 35)
    add_product('Морковь', 40, 'кг', 45)
    add_product('Лук', 30, 'кг', 40)
    add_product('Свекла', 30, 'кг', 35)
    add_product('Огурцы', 20, 'кг', 120)
    add_product('Помидоры', 20, 'кг', 150)
    add_product('Яблоки', 50, 'кг', 100)
    add_product('Бананы', 30, 'кг', 90)
    add_product('Чай', 5, 'кг', 800)
    add_product('Какао', 3, 'кг', 600)
    add_product('Макароны', 25, 'кг', 80)

    print('База данных создана!')
    print('Пользователи:')
    print('  admin / admin123 - Администратор')
    print('  cook / cook123 - Повар')
    print('  student1 / student123 - Ученик')

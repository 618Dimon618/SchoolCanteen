import os
from flask import Flask
from models import db, User, Allergy, Category, MenuItem, MenuItemAllergy, Product, MenuItemIngredient
from db_functions import add_user, add_allergy, add_category, add_menu_item, add_product, add_menu_item_allergy, add_ingredient

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
    student.is_approved = True
    db.session.commit()

    milk = add_allergy('Молоко')
    gluten = add_allergy('Глютен')
    eggs = add_allergy('Яйца')
    nuts = add_allergy('Орехи')
    fish = add_allergy('Рыба')
    citrus = add_allergy('Цитрусовые')
    soy = add_allergy('Соя')
    honey = add_allergy('Мёд')
    chocolate = add_allergy('Шоколад/Какао')
    celery = add_allergy('Сельдерей')
    mustard = add_allergy('Горчица')
    sesame = add_allergy('Кунжут')
    peanut = add_allergy('Арахис')
    shellfish = add_allergy('Моллюски')
    corn = add_allergy('Кукуруза')
    tomato_allergy = add_allergy('Томаты')
    strawberry = add_allergy('Клубника')
    banana_allergy = add_allergy('Бананы')
    kiwi_allergy = add_allergy('Киви')
    cottage_allergy = add_allergy('Творог')

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
        'Сырники': [eggs.id, milk.id, gluten.id, cottage_allergy.id],
        'Блины': [eggs.id, milk.id, gluten.id],
        'Оладьи': [eggs.id, milk.id, gluten.id],
        'Творожная запеканка': [eggs.id, milk.id, cottage_allergy.id],
        'Какао': [milk.id, chocolate.id],
        'Молоко': [milk.id],
        'Апельсин': [citrus.id],
        'Мандарин': [citrus.id],
        'Банан': [banana_allergy.id],
        'Киви': [kiwi_allergy.id],
        'Рыба с рисом': [fish.id],
        'Уха': [fish.id],
        'Котлета с пюре': [gluten.id, eggs.id, milk.id],
        'Тефтели с макаронами': [gluten.id, eggs.id, tomato_allergy.id],
        'Биточки с пюре': [gluten.id, eggs.id, milk.id],
        'Салат оливье': [eggs.id],
        'Борщ': [tomato_allergy.id],
        'Салат огурцы-помидоры': [tomato_allergy.id],
        'Салат греческий': [tomato_allergy.id, milk.id],
        'Гуляш с гречкой': [gluten.id, tomato_allergy.id],
        'Запеканка мясная': [eggs.id, milk.id],
        'Рассольник': [],
        'Винегрет': [],
        'Кисель': [],
        'Морс': [],
    }

    all_created_items = {}

    for day, categories in breakfast_menu.items():
        for cat_id, items in categories.items():
            for name, price in items:
                item = add_menu_item(name, price, cat_id, day)
                all_created_items[item.id] = name
                if name in item_allergies:
                    for allergy_id in item_allergies[name]:
                        add_menu_item_allergy(item.id, allergy_id)

    for day, categories in lunch_menu.items():
        for cat_id, items in categories.items():
            for name, price in items:
                item = add_menu_item(name, price, cat_id, day)
                all_created_items[item.id] = name
                if name in item_allergies:
                    for allergy_id in item_allergies[name]:
                        add_menu_item_allergy(item.id, allergy_id)

    p_milk = add_product('Молоко', 50, 'л', 80)
    p_flour = add_product('Мука', 30, 'кг', 60)
    p_eggs = add_product('Яйца', 100, 'шт', 10)
    p_butter = add_product('Масло сливочное', 20, 'кг', 600)
    p_sugar = add_product('Сахар', 25, 'кг', 70)
    p_salt = add_product('Соль', 10, 'кг', 30)
    p_oat = add_product('Крупа овсяная', 15, 'кг', 90)
    p_buckwheat = add_product('Крупа гречневая', 20, 'кг', 120)
    p_rice = add_product('Крупа рисовая', 20, 'кг', 100)
    p_beef = add_product('Мясо говядина', 30, 'кг', 450)
    p_chicken = add_product('Мясо курица', 40, 'кг', 280)
    p_fish = add_product('Рыба', 25, 'кг', 350)
    p_potato = add_product('Картофель', 100, 'кг', 40)
    p_cabbage = add_product('Капуста', 50, 'кг', 35)
    p_carrot = add_product('Морковь', 40, 'кг', 45)
    p_onion = add_product('Лук', 30, 'кг', 40)
    p_beet = add_product('Свекла', 30, 'кг', 35)
    p_cucumber = add_product('Огурцы', 20, 'кг', 120)
    p_tomato = add_product('Помидоры', 20, 'кг', 150)
    p_apple = add_product('Яблоки', 50, 'кг', 100)
    p_banana = add_product('Бананы', 30, 'кг', 90)
    p_tea = add_product('Чай', 5, 'кг', 800)
    p_cocoa = add_product('Какао', 3, 'кг', 600)
    p_pasta = add_product('Макароны', 25, 'кг', 80)
    p_pear = add_product('Груши', 30, 'кг', 110)
    p_orange = add_product('Апельсины', 20, 'кг', 130)
    p_mandarin = add_product('Мандарины', 20, 'кг', 140)
    p_kiwi = add_product('Киви', 15, 'кг', 200)
    p_cottage = add_product('Творог', 20, 'кг', 300)
    p_sour_cream = add_product('Сметана', 15, 'кг', 250)
    p_millet = add_product('Крупа пшенная', 15, 'кг', 85)
    p_semolina = add_product('Крупа манная', 15, 'кг', 75)
    p_juice_apple = add_product('Сок яблочный', 20, 'л', 120)
    p_juice = add_product('Сок', 20, 'л', 120)
    p_dried_fruit = add_product('Сухофрукты', 10, 'кг', 400)
    p_starch = add_product('Крахмал', 5, 'кг', 150)
    p_peas = add_product('Горох', 10, 'кг', 90)
    p_beans = add_product('Фасоль', 10, 'кг', 150)
    p_noodles = add_product('Лапша', 15, 'кг', 100)
    p_liver = add_product('Печень', 15, 'кг', 320)
    p_radish = add_product('Редис', 10, 'кг', 130)
    p_cheese = add_product('Сыр', 10, 'кг', 500)
    p_olives = add_product('Оливки', 5, 'кг', 600)
    p_berry = add_product('Ягоды', 10, 'кг', 350)
    p_pepper = add_product('Перец', 5, 'кг', 200)
    p_mayo = add_product('Майонез', 5, 'кг', 180)
    p_peas_green = add_product('Горошек зелёный', 10, 'кг', 160)
    p_sausage = add_product('Колбаса', 10, 'кг', 400)
    p_pickle = add_product('Огурцы солёные', 10, 'кг', 150)

    ingredient_map = {
        'Каша овсяная': [(p_oat.id, 0.08), (p_milk.id, 0.2), (p_butter.id, 0.01), (p_salt.id, 0.002), (p_sugar.id, 0.01)],
        'Каша рисовая': [(p_rice.id, 0.08), (p_milk.id, 0.2), (p_butter.id, 0.01), (p_salt.id, 0.002), (p_sugar.id, 0.01)],
        'Каша гречневая': [(p_buckwheat.id, 0.08), (p_milk.id, 0.15), (p_butter.id, 0.01), (p_salt.id, 0.002)],
        'Каша пшенная': [(p_millet.id, 0.08), (p_milk.id, 0.2), (p_butter.id, 0.01), (p_salt.id, 0.002), (p_sugar.id, 0.01)],
        'Каша манная': [(p_semolina.id, 0.06), (p_milk.id, 0.25), (p_butter.id, 0.01), (p_salt.id, 0.002), (p_sugar.id, 0.015)],
        'Омлет': [(p_eggs.id, 3), (p_milk.id, 0.05), (p_butter.id, 0.01), (p_salt.id, 0.002)],
        'Сырники': [(p_cottage.id, 0.15), (p_eggs.id, 1), (p_flour.id, 0.03), (p_sugar.id, 0.02), (p_butter.id, 0.02), (p_sour_cream.id, 0.03)],
        'Блины': [(p_flour.id, 0.1), (p_milk.id, 0.2), (p_eggs.id, 1), (p_sugar.id, 0.02), (p_butter.id, 0.02), (p_salt.id, 0.002)],
        'Оладьи': [(p_flour.id, 0.08), (p_milk.id, 0.15), (p_eggs.id, 1), (p_sugar.id, 0.02), (p_butter.id, 0.02), (p_salt.id, 0.002)],
        'Творожная запеканка': [(p_cottage.id, 0.2), (p_eggs.id, 1), (p_sugar.id, 0.03), (p_butter.id, 0.01), (p_semolina.id, 0.02), (p_sour_cream.id, 0.03)],
        'Яблоко': [(p_apple.id, 0.15)],
        'Банан': [(p_banana.id, 0.15)],
        'Груша': [(p_pear.id, 0.15)],
        'Апельсин': [(p_orange.id, 0.2)],
        'Мандарин': [(p_mandarin.id, 0.15)],
        'Киви': [(p_kiwi.id, 0.1)],
        'Чай': [(p_tea.id, 0.003), (p_sugar.id, 0.015)],
        'Какао': [(p_cocoa.id, 0.02), (p_milk.id, 0.2), (p_sugar.id, 0.02)],
        'Компот': [(p_dried_fruit.id, 0.03), (p_sugar.id, 0.02)],
        'Молоко': [(p_milk.id, 0.25)],
        'Сок яблочный': [(p_juice_apple.id, 0.25)],
        'Сок': [(p_juice.id, 0.25)],
        'Кисель': [(p_starch.id, 0.015), (p_sugar.id, 0.03), (p_berry.id, 0.03)],
        'Морс': [(p_berry.id, 0.04), (p_sugar.id, 0.02)],
        'Борщ': [(p_beet.id, 0.06), (p_cabbage.id, 0.06), (p_potato.id, 0.08), (p_carrot.id, 0.03), (p_onion.id, 0.03), (p_tomato.id, 0.03), (p_beef.id, 0.08), (p_salt.id, 0.003)],
        'Куриный суп': [(p_chicken.id, 0.08), (p_potato.id, 0.08), (p_carrot.id, 0.03), (p_onion.id, 0.02), (p_noodles.id, 0.03), (p_salt.id, 0.003)],
        'Щи': [(p_cabbage.id, 0.1), (p_potato.id, 0.06), (p_carrot.id, 0.03), (p_onion.id, 0.02), (p_beef.id, 0.07), (p_salt.id, 0.003)],
        'Рассольник': [(p_pickle.id, 0.05), (p_potato.id, 0.08), (p_carrot.id, 0.03), (p_onion.id, 0.02), (p_rice.id, 0.02), (p_beef.id, 0.06), (p_salt.id, 0.002)],
        'Гороховый суп': [(p_peas.id, 0.06), (p_potato.id, 0.06), (p_carrot.id, 0.03), (p_onion.id, 0.02), (p_beef.id, 0.06), (p_salt.id, 0.003)],
        'Суп-лапша': [(p_chicken.id, 0.07), (p_noodles.id, 0.05), (p_carrot.id, 0.03), (p_onion.id, 0.02), (p_salt.id, 0.003)],
        'Суп фасолевый': [(p_beans.id, 0.05), (p_potato.id, 0.06), (p_carrot.id, 0.03), (p_onion.id, 0.02), (p_tomato.id, 0.03), (p_salt.id, 0.003)],
        'Уха': [(p_fish.id, 0.12), (p_potato.id, 0.08), (p_carrot.id, 0.03), (p_onion.id, 0.02), (p_salt.id, 0.003)],
        'Суп овощной': [(p_potato.id, 0.08), (p_carrot.id, 0.04), (p_onion.id, 0.03), (p_cabbage.id, 0.05), (p_tomato.id, 0.03), (p_salt.id, 0.003)],
        'Котлета с пюре': [(p_beef.id, 0.1), (p_flour.id, 0.02), (p_eggs.id, 1), (p_onion.id, 0.02), (p_potato.id, 0.2), (p_milk.id, 0.05), (p_butter.id, 0.015), (p_salt.id, 0.003)],
        'Гуляш с гречкой': [(p_beef.id, 0.12), (p_onion.id, 0.03), (p_carrot.id, 0.02), (p_tomato.id, 0.03), (p_flour.id, 0.01), (p_buckwheat.id, 0.08), (p_salt.id, 0.003)],
        'Рыба с рисом': [(p_fish.id, 0.15), (p_rice.id, 0.08), (p_butter.id, 0.01), (p_salt.id, 0.003)],
        'Тефтели с макаронами': [(p_beef.id, 0.1), (p_rice.id, 0.02), (p_eggs.id, 1), (p_onion.id, 0.02), (p_tomato.id, 0.03), (p_pasta.id, 0.08), (p_salt.id, 0.003)],
        'Курица с картофелем': [(p_chicken.id, 0.15), (p_potato.id, 0.2), (p_onion.id, 0.02), (p_butter.id, 0.01), (p_salt.id, 0.003)],
        'Печень с гречкой': [(p_liver.id, 0.12), (p_buckwheat.id, 0.08), (p_onion.id, 0.03), (p_sour_cream.id, 0.03), (p_salt.id, 0.003)],
        'Биточки с пюре': [(p_beef.id, 0.1), (p_flour.id, 0.02), (p_eggs.id, 1), (p_potato.id, 0.2), (p_milk.id, 0.05), (p_butter.id, 0.015), (p_salt.id, 0.003)],
        'Плов': [(p_rice.id, 0.1), (p_beef.id, 0.1), (p_carrot.id, 0.05), (p_onion.id, 0.03), (p_butter.id, 0.02), (p_salt.id, 0.003)],
        'Жаркое': [(p_beef.id, 0.12), (p_potato.id, 0.15), (p_carrot.id, 0.04), (p_onion.id, 0.03), (p_tomato.id, 0.03), (p_salt.id, 0.003)],
        'Запеканка мясная': [(p_beef.id, 0.1), (p_potato.id, 0.15), (p_eggs.id, 1), (p_onion.id, 0.03), (p_cheese.id, 0.03), (p_salt.id, 0.003)],
        'Салат витаминный': [(p_cabbage.id, 0.08), (p_carrot.id, 0.04), (p_apple.id, 0.03), (p_sugar.id, 0.005)],
        'Салат из капусты': [(p_cabbage.id, 0.1), (p_carrot.id, 0.03), (p_onion.id, 0.01), (p_salt.id, 0.002)],
        'Салат огурцы-помидоры': [(p_cucumber.id, 0.08), (p_tomato.id, 0.08), (p_onion.id, 0.02), (p_salt.id, 0.002)],
        'Винегрет': [(p_beet.id, 0.06), (p_potato.id, 0.05), (p_carrot.id, 0.03), (p_pickle.id, 0.03), (p_onion.id, 0.02), (p_peas_green.id, 0.02)],
        'Салат морковный': [(p_carrot.id, 0.1), (p_sugar.id, 0.01), (p_sour_cream.id, 0.02)],
        'Салат свекольный': [(p_beet.id, 0.1), (p_onion.id, 0.02), (p_salt.id, 0.002)],
        'Салат из редиса': [(p_radish.id, 0.08), (p_cucumber.id, 0.05), (p_sour_cream.id, 0.02), (p_salt.id, 0.002)],
        'Салат греческий': [(p_cucumber.id, 0.06), (p_tomato.id, 0.06), (p_pepper.id, 0.03), (p_cheese.id, 0.04), (p_olives.id, 0.02), (p_salt.id, 0.002)],
        'Салат оливье': [(p_potato.id, 0.06), (p_carrot.id, 0.03), (p_eggs.id, 1), (p_pickle.id, 0.03), (p_sausage.id, 0.04), (p_peas_green.id, 0.03), (p_mayo.id, 0.03)],
    }

    for item_id, item_name in all_created_items.items():
        if item_name in ingredient_map:
            for product_id, qty in ingredient_map[item_name]:
                add_ingredient(item_id, product_id, qty)

    print('База данных создана!')
    print('Пользователи:')
    print('  admin / admin123 - Администратор')
    print('  cook / cook123 - Повар')
    print('  student1 / student123 - Ученик')

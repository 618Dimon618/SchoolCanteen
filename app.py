from flask import Flask, render_template, request, redirect
from models_db import db, User

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DATA.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
@app.route("/")
def index():
    return redirect('/login')
@app.route("/login", methods=['GET', 'POST'])
def login():
    action = request.form.get('butt')
    if request.method == 'POST' and action == "login":
        login = request.form['login']
        password = request.form['pass']
        if login == 'admin' and password == '12345':
            return redirect('/admin')
        else:
            return redirect('/login')
    elif request.method == 'POST' and action == "reg":
        return redirect("/register")
    else:
        return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    action = request.form.get('butt')
    if request.method == "POST" and action == "back":
        return redirect("/login")
    elif request.method == "POST" and action == "zareg":
        pass
    else:
        return render_template("register.html")
@app.route("/admin", methods=['GET', 'POST'])
def admin():
    if request.method == "POST":
        return redirect("/login")
    else:
        return render_template("admin_panel.html")


if __name__ == "__main__":
    app.run(debug=True)

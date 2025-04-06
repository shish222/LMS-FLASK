from flask import Flask, request, redirect, render_template, url_for, flash
from data.users_form import UsersFormLogin, UsersFormRegister
from data.db_session import global_init, create_session
from data.__all_models import User
from flask_login import login_user, LoginManager, current_user, logout_user
from data import chat

# from werkzeug.security import generate_password_hash
app = Flask(__name__)
app.config[
    "SECRET_KEY"] = "UkbLH4adfA8b8m9HABoBIvrWjgXZTuzBonhM62dMqfpH7x4h1dIe7ccC_MiJPx6uRaTNCbiqf7vHFxOxZQmsODitPgy9WvCxsgEMH42_OtEnI4-_a_3Fcx8ojc7_qjvh"
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_session = create_session()
    return db_session.query(User).get(int(user_id))


@app.route('/')
def hello_world():
    if not current_user.is_authenticated:
        return redirect("/login")
    return f"Hello, {current_user.name}!"


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")

    form = UsersFormLogin()
    if form.validate_on_submit():
        sess = create_session()
        user = sess.query(User).filter(User.name == form.name.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template("login.html",
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template("login.html", form=form, url_for=url_for)


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect("/")
    form = UsersFormRegister()
    if form.validate_on_submit():
        sess = create_session()
        user = sess.query(User).filter(User.name == form.name.data).first()
        if not user:
            user = User(name=form.name.data)
            user.set_password(form.password.data)
            sess.add(user)
            sess.commit()
        else:
            form.errors = "Неправильное имя или пароль"
    return render_template("register.html", form=form)


if __name__ == '__main__':
    global_init("db/messenger.db")
    app.register_blueprint(chat.blueprint)
    app.run(debug=True)

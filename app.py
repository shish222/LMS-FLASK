from flask import Flask, request, redirect, render_template, url_for, flash
from .data.users_form import UsersFormLogin
from .data.db_session import global_init, create_session
from .data.__all_models import User
from flask_login import login_user, LoginManager, current_user, logout_user

# from werkzeug.security import generate_password_hash
app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_session = create_session()
    return db_session.query(User).get(int(user_id))


@app.route('/')
def hello_world():
    if not current_user.is_authenticated:
        redirect("/login")
    return 'Hello World!'


@app.route("/login", method=["GET", "POST"])
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


@app.route("logout")
def logout():
    logout_user()
    return redirect("/")


if __name__ == '__main__':
    global_init("db/messenger.db")
    app.run()

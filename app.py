import uuid
from flask import Flask, request, redirect, render_template, url_for, jsonify
from data.users_forms import UsersFormLogin, UsersFormRegister
from data.db_session import global_init, create_session
from data.__all_models import User, Chat
from flask_login import login_user, LoginManager, current_user, logout_user
from data import chat as ch
import os

app = Flask(__name__)
app.config[
    "SECRET_KEY"] = "UkbLH4adfA8b8m9HABoBIvrWjgXZTuzBonhM62dMqfpH7x4h1dIe7ccC_MiJPx6uRaTNCbiqf7vHFxOxZQmsODitPgy9WvCxsgEMH42_OtEnI4-_a_3Fcx8ojc7_qjvh"  # 128
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_session = create_session()

    user = db_session.query(User).get(int(user_id))
    user = db_session.merge(user)
    db_session.close()
    return user


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")

    form = UsersFormLogin()
    if form.validate_on_submit():
        sess = create_session()
        try:
            user = sess.query(User).filter(User.name == form.name.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")
            return render_template("login.html",
                                   message="Неправильный логин или пароль",
                                   form=form)
        finally:
            sess.close()
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
        try:
            user = sess.query(User).filter(User.name == form.name.data).first()
            if not user:
                user = User(name=form.name.data, uuid=uuid.uuid4().__str__())
                user.set_password(form.password.data)
                sess.add(user)
                sess.commit()
                login_user(user)
                return redirect("/")
            else:
                form.errors = "Неправильное имя или пароль"
        except Exception as e:
            sess.rollback()
            form.errors = f"Ошибка при регистрации: {str(e)}"
        finally:
            sess.close()
    return render_template("register.html", form=form)


@app.route("/<chat_id>")
async def chat(chat_id):
    if not current_user.is_authenticated:
        return redirect("/login")
    session = create_session()
    user = session.merge(current_user)

    chats = user.chats
    try:
        chat = session.query(Chat).get(chat_id)
        return render_template("chat.html", chat_id=chat_id, chats=chats, current_uuid=user.uuid,
                               current_chat=chat)
    finally:
        session.close()


@app.route("/")
def chat_index():
    if not current_user.is_authenticated:
        return redirect("/login")
    db_session = create_session()
    user = db_session.merge(current_user)
    return render_template("chat.html", chat_id=-1, chats=user.chats, current_uuid=user.uuid)


# Инициализация базы данных
global_init("db/messenger.db")

# Создание директорий для загрузки файлов, если они не существуют
upload_dirs = ["uploads", "uploads/img", "uploads/video"]
for directory in upload_dirs:
    if not os.path.exists(directory):
        os.makedirs(directory)

app.register_blueprint(ch.blueprint)

if __name__ == '__main__':
    app.run(debug=True)

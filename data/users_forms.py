from flask_wtf import FlaskForm
from wtforms.fields.simple import PasswordField, SubmitField, StringField, BooleanField, FileField
from wtforms.validators import DataRequired, length, EqualTo


class UsersFormLogin(FlaskForm):
    name = StringField("Имя", [DataRequired(), length(min=8)])
    password = PasswordField("Пароль", [DataRequired(), length(min=8)])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class UsersFormRegister(FlaskForm):
    name = StringField("Имя", [DataRequired(), length(min=8)])
    password = PasswordField("Пароль", [DataRequired(), length(min=8),
                                        EqualTo("password_confirm", message="Пароли не совпадают")])
    password_confirm = PasswordField("Повторите пароль")
    submit = SubmitField("Регистрация")

from flask_wtf import FlaskForm
from wtforms.fields.simple import PasswordField, SubmitField, StringField, BooleanField
from wtforms.validators import DataRequired, ValidationError, length


class UsersFormLogin(FlaskForm):
    name = StringField("Имя", [DataRequired, length(min=8)])
    password = PasswordField("Пароль", [DataRequired, length(min=8)])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField()

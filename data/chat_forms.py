from flask_wtf import FlaskForm
from wtforms.fields.simple import PasswordField, SubmitField, StringField, BooleanField
from wtforms.validators import DataRequired, length, EqualTo


class CreateChatForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    submit = SubmitField("Создать")


class AddUserForm(FlaskForm):
    username = StringField("Имя пользователя",
                           validators=[DataRequired(), EqualTo("username_confirm", message="Имена не совпадают!")])
    username_confirm = StringField("Повторите имя", validators=[DataRequired()])
    submit = SubmitField("Добавить")

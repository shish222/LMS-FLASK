import flask_login.mixins
import sqlalchemy as sq
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = "users"
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    name = sq.Column(sq.String, nullable=False)
    hashed_password = sq.Column(sq.String, nullable=False)
    chat_id = sq.Column(sq.Integer, sq.ForeignKey("chats.id"))
    chat = relationship("Chat", back_populates="users")

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)


class Message(SqlAlchemyBase):
    __tablename__ = "messages"
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    user = sq.Column(sq.Integer, sq.ForeignKey("users.id"))
    text = sq.Column(sq.String, nullable=False)
    img = sq.Column(sq.String, nullable=True)


class Chat(SqlAlchemyBase):
    __tablename__ = "chats"
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    name = sq.Column(sq.String, nullable=False)
    users = relationship("User", back_populates="chat")

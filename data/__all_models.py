import sqlalchemy as sq
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy.orm import relationship


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = "users"
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    name = sq.Column(sq.String, nulllable=False)
    hashed_password = sq.Column(sq.String, nullable=False)
    chat_id = sq.Column(sq.Integer, sq.ForeignKey("chats.id"))
    chat = relationship("Chat", back_populates="users")


class Message(SqlAlchemyBase):
    __tablename__ = "messages"
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    user = sq.Column(sq.Integer, sq.ForeignKey("users.id"))
    text = sq.Column(sq.String, nullable=False)
    img = sq.Column(sq.String, nulllable=True)


class Chat(SqlAlchemyBase):
    __tablename__ = "chats"
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    name = sq.Column(sq.String, nullable=False)
    users = relationship("User", back_populates="chat")

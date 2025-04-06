from flask_restful import Resource, reqparse
from flask_login import current_user
from flask import redirect, jsonify
from db_session import create_session
from __all_models import User, Chat


class ChatListResource(Resource):
    def get(self):
        if not current_user.is_authenticated:
            return redirect('/login')
        session = create_session()
        print(current_user.chat)


class ChatResource(Resource):
    # Создание нового чата
    def post(self):
        if not current_user.is_authenticated:
            return redirect('/login')
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=False)
        args = parser.parse_args()
        session = create_session()
        chat = Chat(name=args['name'])
        chat.users.append(current_user)
        session.add(chat)
        session.commit()
        return jsonify({"chat_id": chat.id})

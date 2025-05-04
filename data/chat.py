import json
import os.path

from flask.blueprints import Blueprint
from flask import redirect, Response, make_response, jsonify, request, send_from_directory
from flask_login import current_user
from .__all_models import Chat, User, Message
from .db_session import create_session
from werkzeug.utils import secure_filename

blueprint = Blueprint('chat', __name__)


def message_serializer(message, user_id):
    message_s = {'text': message.text.replace("<", "&lt;").replace(">", "&gt;"), "img": message.img,
                 "video": message.video}
    session = create_session()
    user = session.query(User).get(message.user)
    if user.id == user_id:
        message_s["type"] = "sent"
    else:
        message_s["type"] = "received"
    message_s["username"] = user.name
    return message_s


@blueprint.route("/streaming_chat/<int:chat_id>")
def streaming_chat(chat_id):
    if not current_user.is_authenticated:
        return redirect('/login')
    db_session = create_session()
    chat = db_session.query(Chat).filter(Chat.id == chat_id).all()
    user_id = current_user.id
    if not chat:
        return make_response(jsonify({'error': 'Chat not found'}), 404)

    if not current_user in chat[0].users:
        return make_response(jsonify({'error': 'Chat not found'}), 404)

    def stream():
        messages = db_session.query(Message).filter_by(chat_id=chat_id).all()
        for message in messages:
            data = message_serializer(message, user_id)
            data = json.dumps(data)
            yield f"data: {data}\n\n"
        last_message = get_last_message()
        while True:
            messages = db_session.query(Message).filter(Message.id > last_message, Message.chat_id == chat_id).all()
            for message in messages:
                last_message = message.id
                data = message_serializer(message, user_id)
                data = json.dumps(data)
                yield f"data: {data}\n\n"

    def get_last_message():
        message = db_session.query(Message).filter_by(chat_id=chat_id).all()
        if not message:
            return 0
        return message[-1].id

    return Response(stream(), mimetype="text/event-stream")


@blueprint.route("/find_user_by_uuid", methods=['POST'])
def find_user_by_uuid():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Необходима авторизация"})

    uuid = request.json.get('uuid')
    if not uuid:
        return jsonify({"success": False, "message": "UUID не указан"})

    session = create_session()
    user = session.query(User).filter(User.uuid == uuid).first()

    if not user:
        return jsonify({"success": False, "message": "Пользователь не найден"})

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "uuid": user.uuid
        }
    })


@blueprint.route("/add_user_to_chat", methods=['POST'])
def add_user_to_chat():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Необходима авторизация"})
    data = request.form.to_dict()
    uuid = data.get('uuid')
    chat_id = data.get('chat_id')

    if not uuid or not chat_id:
        return jsonify({"success": False, "message": "Не указаны необходимые параметры"})

    session = create_session()
    user = session.query(User).filter(User.uuid == uuid).first()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()

    if not user:
        return jsonify({"success": False, "message": "Пользователь не найден"})

    if not chat:
        return jsonify({"success": False, "message": "Чат не найден"})

    # Проверка, что пользователь уже не добавлен
    if user in chat.users:
        return jsonify({"success": False, "message": "Пользователь уже добавлен в чат"})

    chat.users.append(user)
    session.commit()

    # Возвращаем информацию о добавленном пользователе
    return jsonify({
        "success": True,
        "message": "Пользователь успешно добавлен в чат",
        "user": {
            "id": user.id,
            "name": user.name,
            "first_letter": user.name[0].upper()
        },
        "chat_id": chat.id,
        "users_count": len(chat.users)
    })


@blueprint.route("/remove_user_from_chat", methods=['POST'])
def remove_user_from_chat():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Необходима авторизация"})

    user_id = request.json.get('user_id')
    chat_id = request.json.get('chat_id')

    if not user_id or not chat_id:
        return jsonify({"success": False, "message": "Не указаны необходимые параметры"})

    session = create_session()
    user = session.query(User).get(user_id)
    chat = session.query(Chat).get(chat_id)

    if not user:
        return jsonify({"success": False, "message": "Пользователь не найден"})

    if not chat:
        return jsonify({"success": False, "message": "Чат не найден"})

    # Проверка, что текущий пользователь участник чата
    if current_user not in chat.users:
        return jsonify({"success": False, "message": "У вас нет прав для выполнения этого действия"})

    # Нельзя удалить самого себя
    if user.id == current_user.id:
        return jsonify({"success": False, "message": "Вы не можете удалить себя из чата"})

    # Проверка, что пользователь находится в чате
    if user not in chat.users:
        return jsonify({"success": False, "message": "Пользователь не состоит в этом чате"})

    chat.users.remove(user)
    session.commit()

    return jsonify({"success": True, "message": f"Пользователь {user.name} удален из чата"})


@blueprint.route("/create_chat", methods=['GET', 'POST'])
def create_chat():
    if not current_user.is_authenticated:
        return redirect('/login')
    session = create_session()
    params = request.form.to_dict()
    chat = Chat(name=params["name"])
    chat.users.append(current_user)
    local_chat = session.merge(chat)
    session.add(local_chat)
    session.commit()
    return make_response(jsonify({"Create": "OK"}), 201)


@blueprint.route("/create_message", methods=['POST'])
def create_message():
    if not current_user.is_authenticated:
        return redirect('/login')
    params = request.form.to_dict()
    session = create_session()
    chat = session.query(Chat).get(params['chat_id'])
    if not chat or not current_user in chat.users:
        return make_response(jsonify({'error': 'Chat not found'}), 404)
    if request.files:
        if 'image' in request.files:
            filename = "img/" + secure_filename(request.files['image'].filename)
            request.files['image'].save(os.path.join("uploads", filename))
            message = Message(user=current_user.id, text=params['text'], img=filename)
        elif 'video' in request.files:
            filename = "video/" + secure_filename(request.files['video'].filename)
            request.files['video'].save(os.path.join("uploads", filename))
            message = Message(user=current_user.id, text=params['text'], video=filename)
    else:
        message = Message(user=current_user.id, text=params['text'])
    chat.messages.append(message)
    session.add(message)
    session.commit()
    return make_response(jsonify({"Create": "OK"}), 201)


@blueprint.route("/uploads/<t>/<filename>")
def uploaded_file(t, filename):
    if not current_user.is_authenticated:
        return make_response(jsonify({'error': 'Not found'}), 404)
    return send_from_directory("uploads", path=os.path.join(t, filename).__str__(), as_attachment=True)

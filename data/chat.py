import json
import os.path

import html
from flask.blueprints import Blueprint
from flask import redirect, Response, make_response, jsonify, request, send_from_directory
from flask_login import current_user
from .__all_models import Chat, User, Message
from .db_session import create_session
from werkzeug.utils import secure_filename

# Константы для работы с файлами
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov'}

blueprint = Blueprint('chat', __name__)


def message_serializer(message, user_id):
    # Используем html.escape для более надежной защиты от XSS
    message_s = {'text': message.text, "img": message.img,
                 "video": message.video}
    session = create_session()
    try:
        user = session.query(User).get(message.user)
        if user.id == user_id:
            message_s["type"] = "sent"
        else:
            message_s["type"] = "received"
        message_s["username"] = user.name
        return message_s
    finally:
        session.close()


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
    try:
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
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка при поиске пользователя: {str(e)}"})
    finally:
        session.close()


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
    try:
        c_user = session.merge(current_user)
        user = session.query(User).filter(User.uuid == uuid).first()
        user = session.merge(user)
        chat = session.query(Chat).filter(Chat.id == chat_id).first()

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"})

        if not chat:
            return jsonify({"success": False, "message": "Чат не найден"})

        # Проверка, что текущий пользователь участник чата
        if c_user not in chat.users:
            return jsonify({"success": False, "message": "У вас нет прав для добавления пользователей в этот чат"})

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
    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "message": f"Ошибка при добавлении пользователя: {str(e)}"})
    finally:
        session.close()


@blueprint.route("/remove_user_from_chat", methods=['POST'])
def remove_user_from_chat():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Необходима авторизация"})

    user_id = request.json.get('user_id')
    chat_id = request.json.get('chat_id')

    if not user_id or not chat_id:
        return jsonify({"success": False, "message": "Не указаны необходимые параметры"})

    session = create_session()
    try:
        user = session.query(User).get(user_id)
        user = session.merge(user)
        chat = session.query(Chat).get(chat_id)
        c_user = session.merge(current_user)

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"})

        if not chat:
            return jsonify({"success": False, "message": "Чат не найден"})

        # Проверка, что текущий пользователь участник чата
        if c_user not in chat.users:
            return jsonify({"success": False, "message": "У вас нет прав для выполнения этого действия"})

        # Нельзя удалить самого себя
        if user.id == c_user.id:
            return jsonify({"success": False, "message": "Вы не можете удалить себя из чата"})

        # Проверка, что пользователь находится в чате
        if user not in chat.users:
            return jsonify({"success": False, "message": "Пользователь не состоит в этом чате"})

        chat.users.remove(user)
        session.commit()

        return jsonify({"success": True, "message": f"Пользователь {user.name} удален из чата"})
    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "message": f"Ошибка при удалении пользователя: {str(e)}"})
    finally:
        session.close()


@blueprint.route("/create_chat", methods=['GET', 'POST'])
def create_chat():
    if not current_user.is_authenticated:
        return redirect('/login')

    session = create_session()
    try:
        params = request.form.to_dict()

        if "name" not in params or not params["name"].strip():
            return make_response(jsonify({'error': 'Имя чата не может быть пустым'}), 400)

        chat = Chat(name=params["name"])
        user = session.merge(current_user)
        chat.users.append(user)
        local_chat = session.merge(chat)
        session.add(local_chat)
        session.commit()

        return make_response(jsonify({
            "Create": "OK",
            "chat_id": local_chat.id,
            "chat_name": local_chat.name
        }), 201)
    except Exception as e:
        session.rollback()
        return make_response(jsonify({'error': f'Ошибка при создании чата: {str(e)}'}), 500)
    finally:
        session.close()


def allowed_image_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def allowed_video_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


def ensure_upload_dirs():
    # Проверяем и создаем необходимые директории для загрузки файлов
    upload_dirs = ["uploads", "uploads/img", "uploads/video"]
    for directory in upload_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)


@blueprint.route("/create_message", methods=['POST'])
def create_message():
    if not current_user.is_authenticated:
        return redirect('/login')

    # Обеспечиваем наличие директорий для загрузки
    ensure_upload_dirs()

    params = request.form.to_dict()
    session = create_session()
    try:
        chat = session.query(Chat).get(params['chat_id'])
        c_user = session.merge(current_user)
        if not chat or not c_user in chat.users:
            return make_response(jsonify({'error': 'Chat not found'}), 404)

        message = None

        if request.files:
            if 'image' in request.files and request.files['image'].filename:
                image_file = request.files['image']
                if not allowed_image_file(image_file.filename):
                    return make_response(jsonify({'error': 'Неподдерживаемый формат изображения'}), 400)

                # Проверка размера файла
                image_file.seek(0, os.SEEK_END)
                file_size = image_file.tell()
                image_file.seek(0)

                if file_size > MAX_FILE_SIZE:
                    return make_response(jsonify({'error': 'Размер файла превышает 10 МБ'}), 400)

                try:
                    filename = "img/" + secure_filename(image_file.filename)
                    file_path = os.path.join("uploads", filename)
                    image_file.save(file_path)
                    message = Message(user=c_user.id, text=params['text'], img=filename)
                except Exception as e:
                    return make_response(jsonify({'error': f'Ошибка при сохранении изображения: {str(e)}'}), 500)

            elif 'video' in request.files and request.files['video'].filename:
                video_file = request.files['video']
                if not allowed_video_file(video_file.filename):
                    return make_response(jsonify({'error': 'Неподдерживаемый формат видео'}), 400)

                # Проверка размера файла
                video_file.seek(0, os.SEEK_END)
                file_size = video_file.tell()
                video_file.seek(0)

                if file_size > MAX_FILE_SIZE:
                    return make_response(jsonify({'error': 'Размер файла превышает 10 МБ'}), 400)

                try:
                    filename = "video/" + secure_filename(video_file.filename)
                    file_path = os.path.join("uploads", filename)
                    video_file.save(file_path)
                    message = Message(user=c_user.id, text=params['text'], video=filename)
                except Exception as e:
                    return make_response(jsonify({'error': f'Ошибка при сохранении видео: {str(e)}'}), 500)

        if message is None:
            message = Message(user=c_user.id, text=params['text'])

        chat.messages.append(message)
        session.add(message)
        session.commit()
        return make_response(jsonify({"Create": "OK"}), 201)
    except Exception as e:
        session.rollback()
        return make_response(jsonify({'error': f'Внутренняя ошибка: {str(e)}'}), 500)
    finally:
        session.close()


@blueprint.route("/uploads/<t>/<filename>")
def uploaded_file(t, filename):
    if not current_user.is_authenticated:
        return make_response(jsonify({'error': 'Not found'}), 404)
    return send_from_directory("uploads", path=os.path.join(t, filename).__str__(), as_attachment=True)

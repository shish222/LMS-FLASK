import json
import os.path

from flask.blueprints import Blueprint
from flask import render_template, redirect, Response, make_response, jsonify, url_for, request, send_from_directory
from flask_login import current_user
from flask_restful import Api, Resource
from .__all_models import Chat, User, Message
from .chat_forms import CreateChatForm, AddUserForm
from .db_session import create_session
from json import dumps
from werkzeug.utils import secure_filename

blueprint = Blueprint('chat', __name__)
api = Api(blueprint)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ["jpg", "jpeg", "png", "webp"]


def message_serializer(message, user_id):
    message_s = {}
    message_s['text'] = message.text.replace("<", "&lt;").replace(">", "&gt;")
    message_s["img"] = message.img
    session = create_session()
    user = session.query(User).get(message.user)
    if user.id == user_id:
        message_s["type"] = "sent"
    else:
        message_s["type"] = "received"
    message_s["username"] = user.name
    return message_s


@blueprint.route('/<int:chat_id>/add_user_chat/', methods=['POST'])
def add_user_chat(chat_id):
    if not current_user.is_authenticated:
        return redirect('/login')
    form = AddUserForm()
    if form.validate_on_submit():
        session = create_session()
        chat = session.query(Chat).filter_by(current_user in Chat.users, id=chat_id).one()
        if not chat:
            return make_response(jsonify({"Error": "Chat not found"}), 404)
        user = session.query(User).filter_by(id=form.username.data).one()
        chat.users.append(user)
        local_chat = session.merge(chat)
        session.add(local_chat)
        session.commit()
        return redirect(f'/{chat.id}')
    return render_template("add_user.html", form=form, url_for=url_for)


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


@blueprint.route("/create_chat", methods=['GET', 'POST'])
def create_chat():
    if not current_user.is_authenticated:
        return redirect('/login')
    form = CreateChatForm()
    if form.validate_on_submit():
        session = create_session()
        chat = Chat(name=form.name.data)
        chat.users.append(current_user)
        # c = current_user
        local_chat = session.merge(chat)
        session.add(local_chat)
        session.commit()
        return redirect(f'/{chat.id}')
    return render_template("create_chat.html", form=form, url_for=url_for)


@blueprint.route("/create_message", methods=['POST'])
def create_message():
    if not current_user.is_authenticated:
        return redirect('/login')
    params = request.form.to_dict()
    session = create_session()
    chat = session.query(Chat).get(params['chat_id'])
    if not chat:
        return make_response(jsonify({'error': 'Chat not found'}), 404)
    if not current_user in chat.users:
        return make_response(jsonify({'error': 'Chat not found'}), 404)
    r = request
    if request.files:
        if 'image' in request.files:
            filename = secure_filename(request.files['image'].filename)
            request.files['image'].save(os.path.join("uploads/img", filename))
            message = Message(user=current_user.id, text=params['text'], img=filename)
        elif 'video' in request.files:
            filename = secure_filename(request.files['video'].filename)
            request.files['video'].save(os.path.join("uploads/video", filename))
            message = Message(user=current_user.id, text=params['text'], video=filename)
    else:
        message = Message(user=current_user.id, text=params['text'])
    chat.messages.append(message)
    session.add(message)
    session.commit()
    return make_response(jsonify({"Create": "OK"}), 201)


@blueprint.route("/uploads/<filename>")
def uploaded_file(filename):
    if not current_user.is_authenticated:
        return make_response(jsonify({'error': 'Not found'}), 404)
    return send_from_directory("uploads", path=filename, as_attachment=True)


@blueprint.route("/open_media/<path>")
def open_media(path):
    if not current_user.is_authenticated:
        return make_response(jsonify({'error': 'Not found'}), 404)
    _type = path.split("/")[-2]
    return render_template("open_media.html", type=_type, path=path)

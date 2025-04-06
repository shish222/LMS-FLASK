from flask.blueprints import Blueprint
from flask import render_template, redirect
from flask_login import current_user
from flask_restful import Api, Resource
from .__all_models import Chat
from .db_session import create_session

blueprint = Blueprint('chat', __name__)
api = Api(blueprint)

@blueprint.route('/add_user_chat', methods=['POST'])
def add_user_chat():
    if not current_user.is_authenticated:
        return redirect('/login')

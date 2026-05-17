from flask import Blueprint
from app.controllers.auth_controller import login_form, login, logout

auth = Blueprint(
    'auth',
    __name__,
    url_prefix='/auth'
)

# Routes
auth.route('/login', methods=['GET'])(login_form)
auth.route('/login', methods=['POST'])(login)
auth.route('/logout', methods=['GET'])(logout)

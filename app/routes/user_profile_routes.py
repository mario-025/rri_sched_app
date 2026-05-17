from flask import Blueprint
from app.controllers.user_profile_controller import user_profile, user_my_schedules

user_profile_bp = Blueprint(
    'user_profile',
    __name__,
    url_prefix='/user'
)

# Routes
user_profile_bp.route('/profile')(user_profile)
user_profile_bp.route('/schedules')(user_my_schedules)

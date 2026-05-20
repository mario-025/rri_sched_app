from flask import Blueprint
from app.controllers.user_profile_controller import (
    user_profile, 
    user_my_schedules,
    telegram_settings,
    telegram_link,
    telegram_verify,
    telegram_status,
    telegram_verify_from_bot,
    telegram_unlink
)

user_profile_bp = Blueprint(
    'user_profile',
    __name__,
    url_prefix='/user'
)

# Routes
user_profile_bp.route('/profile')(user_profile)
user_profile_bp.route('/schedules')(user_my_schedules)

# Telegram routes
user_profile_bp.route('/telegram-settings')(telegram_settings)
user_profile_bp.route('/telegram-link', methods=['POST'])(telegram_link)
user_profile_bp.route('/telegram-verify', methods=['POST'])(telegram_verify)
user_profile_bp.route('/telegram-status', methods=['GET'])(telegram_status)
user_profile_bp.route('/telegram-unlink', methods=['POST'])(telegram_unlink)

# Public endpoint (no login required) for bot verification
user_profile_bp.route('/telegram-verify-from-bot', methods=['POST'])(telegram_verify_from_bot)

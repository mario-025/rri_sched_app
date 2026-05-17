from flask import Blueprint

from app.controllers.user_controller import (
    create_user,
    get_all_users,
    create_form,
    edit_form,
    update_user,
    delete_user,
    user_detail,
    api_generate_password
)

user_bp = Blueprint(
    "user",
    __name__
)

# List all users
user_bp.route(
    "/",
    methods=["GET"]
)(get_all_users)

# Create form
user_bp.route(
    "/create",
    methods=["GET"]
)(create_form)

# Save new user
user_bp.route(
    "/create",
    methods=["POST"]
)(create_user)

# User detail
user_bp.route(
    "/<int:user_id>/detail",
    methods=["GET"]
)(user_detail)

# Edit form
user_bp.route(
    "/<int:user_id>/edit",
    methods=["GET"]
)(edit_form)

# Update user
user_bp.route(
    "/<int:user_id>/edit",
    methods=["POST"]
)(update_user)

# Delete user
user_bp.route(
    "/<int:user_id>/delete",
    methods=["POST"]
)(delete_user)

# Generate random password (API)
user_bp.route(
    "/api/generate-password",
    methods=["GET"]
)(api_generate_password)
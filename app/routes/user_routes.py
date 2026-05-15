from flask import Blueprint

from app.controllers.user_controller import (
    create_user,
    get_all_users,
    create_form,
    edit_form,
    update_user,
    delete_user
)

user_bp = Blueprint(
    "user",
    __name__
)

user_bp.route(
    "/",
    methods=["GET"]
)(get_all_users)

user_bp.route(
    "/create",
    methods=["GET"]
)(create_form)

user_bp.route(
    "/create",
    methods=["POST"]
)(create_user)

# form edit
user_bp.route(
    "/<int:id>/edit",
    methods=["GET"]
)(edit_form)

# update data
user_bp.route(
    "/<int:id>/edit",
    methods=["POST"]
)(update_user)

# delete
user_bp.route(
    "/<int:id>/delete",
    methods=["POST"]
)(delete_user)
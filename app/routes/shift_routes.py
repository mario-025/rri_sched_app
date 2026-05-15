from flask import Blueprint
from app.controllers.shift_controller import (
    list_shifts,
    shift_form,
    create_shift,
    edit_shift_form,
    update_shift,
    delete_shift
)

shift_bp = Blueprint(
    'shift',
    __name__,
    url_prefix='/shifts'
)

# Routes
shift_bp.route('/', methods=['GET'])(list_shifts)
shift_bp.route('/create', methods=['GET'])(shift_form)
shift_bp.route('/', methods=['POST'])(create_shift)
shift_bp.route('/<int:shift_id>/edit', methods=['GET'])(edit_shift_form)
shift_bp.route('/<int:shift_id>', methods=['POST'])(update_shift)
shift_bp.route('/<int:shift_id>/delete', methods=['POST'])(delete_shift)

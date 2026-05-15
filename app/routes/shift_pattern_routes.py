from flask import Blueprint
from app.controllers.shift_pattern_controller import (
    list_patterns,
    pattern_form,
    create_pattern,
    edit_pattern_form,
    update_pattern,
    delete_pattern
)

shift_pattern_bp = Blueprint(
    'shift_pattern',
    __name__,
    url_prefix='/shift-patterns'
)

# Routes
shift_pattern_bp.route('/', methods=['GET'])(list_patterns)
shift_pattern_bp.route('/create', methods=['GET'])(pattern_form)
shift_pattern_bp.route('/', methods=['POST'])(create_pattern)
shift_pattern_bp.route('/<int:pattern_id>/edit', methods=['GET'])(edit_pattern_form)
shift_pattern_bp.route('/<int:pattern_id>', methods=['POST'])(update_pattern)
shift_pattern_bp.route('/<int:pattern_id>/delete', methods=['POST'])(delete_pattern)

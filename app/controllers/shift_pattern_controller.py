from flask import render_template, request, redirect, url_for, flash, jsonify
from app.config.database import db
from app.models.shift_pattern import ShiftPattern
from app.models.shift_patern_detail import ShiftPatternDetail
from app.models.shift import Shift
from app.controllers.auth_controller import login_required


@login_required
def list_patterns():
    """List all shift patterns"""
    patterns = ShiftPattern.query.all()
    return render_template('shift_patterns/index.html', patterns=patterns)


@login_required
def pattern_form():
    """Show form for create new pattern"""
    shifts = Shift.query.order_by(Shift.shift_index).all()
    return render_template('shift_patterns/form.html', pattern=None, shifts=shifts)


@login_required
def create_pattern():
    """Save new pattern with inline details"""
    try:
        pattern_name = request.form.get('pattern_name')
        description = request.form.get('description', '')
        
        if not pattern_name:
            flash('Nama pattern harus diisi', 'danger')
            return redirect(url_for('shift_pattern.pattern_form'))
        
        # Check duplicate
        existing = ShiftPattern.query.filter_by(pattern_name=pattern_name).first()
        if existing:
            flash(f'Pattern {pattern_name} sudah ada', 'danger')
            return redirect(url_for('shift_pattern.pattern_form'))
        
        pattern = ShiftPattern(
            pattern_name=pattern_name,
            description=description
        )
        
        db.session.add(pattern)
        db.session.flush()  # Get pattern ID
        
        # Add details
        shift_ids = request.form.getlist('shift_ids[]')
        worker_counts = request.form.getlist('worker_counts[]')
        
        if not shift_ids:
            flash('Minimal 1 shift harus ditambahkan ke pattern', 'danger')
            db.session.rollback()
            return redirect(url_for('shift_pattern.pattern_form'))
        
        for shift_id, worker_count in zip(shift_ids, worker_counts):
            detail = ShiftPatternDetail(
                pattern_id=pattern.id,
                shift_id=int(shift_id),
                worker_count=int(worker_count) if worker_count else 1
            )
            db.session.add(detail)
        
        db.session.commit()
        flash(f'Pattern {pattern_name} berhasil ditambahkan', 'success')
        return redirect(url_for('shift_pattern.list_patterns'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('shift_pattern.pattern_form'))


@login_required
def edit_pattern_form(pattern_id):
    """Show form for edit pattern with details"""
    pattern = ShiftPattern.query.get_or_404(pattern_id)
    shifts = Shift.query.order_by(Shift.shift_index).all()
    return render_template('shift_patterns/form.html', pattern=pattern, shifts=shifts)


@login_required
def update_pattern(pattern_id):
    """Update pattern and details"""
    try:
        pattern = ShiftPattern.query.get_or_404(pattern_id)
        
        pattern.pattern_name = request.form.get('pattern_name')
        pattern.description = request.form.get('description', '')
        
        if not pattern.pattern_name:
            flash('Nama pattern harus diisi', 'danger')
            return redirect(url_for('shift_pattern.edit_pattern_form', pattern_id=pattern_id))
        
        # Check duplicate (excluding current pattern)
        existing = ShiftPattern.query.filter(
            ShiftPattern.pattern_name == pattern.pattern_name,
            ShiftPattern.id != pattern_id
        ).first()
        if existing:
            flash(f'Pattern {pattern.pattern_name} sudah ada', 'danger')
            return redirect(url_for('shift_pattern.edit_pattern_form', pattern_id=pattern_id))
        
        # Delete old details
        ShiftPatternDetail.query.filter_by(pattern_id=pattern_id).delete()
        
        # Add new details
        shift_ids = request.form.getlist('shift_ids[]')
        worker_counts = request.form.getlist('worker_counts[]')
        
        if not shift_ids:
            flash('Minimal 1 shift harus ditambahkan ke pattern', 'danger')
            db.session.rollback()
            return redirect(url_for('shift_pattern.edit_pattern_form', pattern_id=pattern_id))
        
        for shift_id, worker_count in zip(shift_ids, worker_counts):
            detail = ShiftPatternDetail(
                pattern_id=pattern.id,
                shift_id=int(shift_id),
                worker_count=int(worker_count) if worker_count else 1
            )
            db.session.add(detail)
        
        db.session.commit()
        flash(f'Pattern {pattern.pattern_name} berhasil diperbarui', 'success')
        return redirect(url_for('shift_pattern.list_patterns'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('shift_pattern.edit_pattern_form', pattern_id=pattern_id))


@login_required
def delete_pattern(pattern_id):
    """Delete pattern and its details"""
    try:
        pattern = ShiftPattern.query.get_or_404(pattern_id)
        pattern_name = pattern.pattern_name
        
        # Delete details first
        ShiftPatternDetail.query.filter_by(pattern_id=pattern_id).delete()
        
        # Delete pattern
        db.session.delete(pattern)
        db.session.commit()
        
        flash(f'Pattern {pattern_name} berhasil dihapus', 'success')
        return redirect(url_for('shift_pattern.list_patterns'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('shift_pattern.list_patterns'))

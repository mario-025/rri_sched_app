from flask import render_template, request, redirect, url_for, flash
from app.config.database import db
from app.models.shift import Shift
from app.models.schedule import Schedule


def list_shifts():
    """List all shifts"""
    shifts = Shift.query.order_by(Shift.shift_index).all()
    return render_template('shifts/index.html', shifts=shifts)


def get_shift_usage_count(shift_id):
    """Get how many schedules use this shift"""
    return Schedule.query.filter_by(shift_id=shift_id).count()


def shift_form():
    """Show form for create new shift"""
    return_to = request.args.get('return_to', None)
    return render_template('shifts/form.html', shift=None, return_to=return_to)


def create_shift():
    """Save new shift"""
    try:
        shift_index = request.form.get('shift_index', type=int)
        shift_name = request.form.get('shift_name')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        score = request.form.get('score', type=int, default=1)
        return_to = request.form.get('return_to', None)
        
        # Validate
        if not all([shift_index, shift_name, start_time, end_time]):
            flash('Semua field harus diisi', 'danger')
            return redirect(url_for('shift.shift_form', return_to=return_to) if return_to else url_for('shift.shift_form'))
        
        # Check duplicate shift_index
        existing = Shift.query.filter_by(shift_index=shift_index).first()
        if existing:
            flash(f'Shift Index {shift_index} sudah ada', 'danger')
            return redirect(url_for('shift.shift_form', return_to=return_to) if return_to else url_for('shift.shift_form'))
        
        shift = Shift(
            shift_index=shift_index,
            shift_name=shift_name,
            start_time=start_time,
            end_time=end_time,
            score=score
        )
        
        db.session.add(shift)
        db.session.commit()
        
        flash(f'Shift {shift_name} berhasil ditambahkan', 'success')
        
        # Return ke halaman yang sesuai
        if return_to == 'shift-patterns-create':
            return redirect(url_for('shift_pattern.pattern_form'))
        elif return_to and return_to.startswith('shift-patterns-edit-'):
            pattern_id = return_to.split('-')[-1]
            return redirect(url_for('shift_pattern.edit_pattern_form', pattern_id=pattern_id))
        else:
            return redirect(url_for('shift.list_shifts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return_to = request.form.get('return_to', None)
        return redirect(url_for('shift.shift_form', return_to=return_to) if return_to else url_for('shift.shift_form'))


def edit_shift_form(shift_id):
    """Show form for edit shift"""
    shift = Shift.query.get_or_404(shift_id)
    usage_count = get_shift_usage_count(shift_id)
    can_edit = usage_count == 0
    return_to = request.args.get('return_to', None)
    return render_template('shifts/form.html', shift=shift, usage_count=usage_count, can_edit=can_edit, return_to=return_to)


def update_shift(shift_id):
    """Update existing shift"""
    try:
        shift = Shift.query.get_or_404(shift_id)
        
        shift.shift_index = request.form.get('shift_index', type=int)
        shift.shift_name = request.form.get('shift_name')
        shift.start_time = request.form.get('start_time')
        shift.end_time = request.form.get('end_time')
        shift.score = request.form.get('score', type=int, default=1)
        
        # Check duplicate shift_index (excluding current shift)
        existing = Shift.query.filter(
            Shift.shift_index == shift.shift_index,
            Shift.id != shift_id
        ).first()
        if existing:
            flash(f'Shift Index {shift.shift_index} sudah digunakan shift lain', 'danger')
            return redirect(url_for('shift.edit_shift_form', shift_id=shift_id))
        
        db.session.commit()
        flash(f'Shift {shift.shift_name} berhasil diperbarui', 'success')
        return redirect(url_for('shift.list_shifts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('shift.edit_shift_form', shift_id=shift_id))


def delete_shift(shift_id):
    """Delete shift"""
    try:
        shift = Shift.query.get_or_404(shift_id)
        shift_name = shift.shift_name
        
        # Check if shift is used in pattern details
        if shift.pattern_details:
            flash(f'Tidak bisa menghapus {shift_name} karena sudah digunakan di Shift Pattern', 'danger')
            return redirect(url_for('shift.list_shifts'))
        
        db.session.delete(shift)
        db.session.commit()
        
        flash(f'Shift {shift_name} berhasil dihapus', 'success')
        return redirect(url_for('shift.list_shifts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('shift.list_shifts'))

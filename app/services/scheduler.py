import datetime
import calendar
import random
from sqlalchemy.orm import joinedload
from app.models.user import User
from app.models.shift_pattern import ShiftPattern
from app.models.shift_patern_detail import ShiftPatternDetail
days_mapping = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"}

def generate_dates(year, month):
    total_days = calendar.monthrange(year, month)[1]
    for day_num in range(1, total_days + 1):
        yield datetime.date( year, month, day_num)

def get_pattern_for_day(work_day_index, patterns):
    return patterns[
        work_day_index % len(patterns)
    ]

def select_user(users, assigned_today):
    available_users = [
        u for u in users
        if u.id not in assigned_today
    ]
    # user habis
    if not available_users:
        return None
    min_score = min(
        u.score
        for u in available_users
    )
    candidates = [
        u for u in available_users
        if u.score == min_score
    ]
    return random.choice(
        candidates
    )

def generate_schedule(year, month, days_off=None, patterns_to_use=None):
    all_patterns = (
    ShiftPattern.query
    .options(
        joinedload(
            ShiftPattern.details
        ).joinedload(
            ShiftPatternDetail.shift
        )).all()
    )
    users = User.query.all()
    
    # Filter patterns berdasarkan patterns_to_use jika diberikan
    # PENTING: Maintain urutan sesuai patterns_to_use, bukan urutan database
    if patterns_to_use:
        patterns = [p for pid in patterns_to_use for p in all_patterns if p.id == pid]
    else:
        patterns = all_patterns
    
    # validasi data
    if not users:
        return []
    if not patterns:
        return []
    if days_off is None:
        days_off = []

    generated_schedule = []
    work_day_index = 0

    for current_date in generate_dates(year, month):
        weekday = current_date.weekday()
        if weekday in days_off:
            continue
        assigned_today = set()
        pattern = get_pattern_for_day(
            work_day_index,
            patterns
        )

        for detail in sorted(pattern.details,key=lambda d: d.shift.shift_index):
            shift = detail.shift
            for _ in range(detail.worker_count):
                user = select_user(users,assigned_today)
                if not user:
                    break
                assigned_today.add(user.id)

                # update score
                user.score += shift.score

                generated_schedule.append({
                    "user_id": user.id,
                    "shift_id":shift.id,
                    "work_date": current_date.isoformat(),
                    "user": user.fullname,
                    "user_score": user.score,
                    "day" : days_mapping[weekday],
                    "shift": shift.shift_name,
                    "shift_score" : shift.score,
                    "pattern": pattern.pattern_name
                })
        work_day_index += 1
    return generated_schedule
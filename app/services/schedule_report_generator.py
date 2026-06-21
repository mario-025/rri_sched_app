import datetime
import calendar
from collections import defaultdict
from app.models.schedule import Schedule
from app.models.user import User
from app.models.shift import Shift


DAYS_MAPPING = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu"
}

MONTHS_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember"
}


def get_schedule_report(year, month, schedule_type=None):
    """
    Generate jadwal dalam format tabel untuk laporan.
    
    Returns:
        dict: {
            'year': int,
            'month': int,
            'month_name': str,
            'schedule_data': [
                {
                    'date': '01 Juni 2026',
                    'day_name': 'Senin',
                    'shifts': {
                        'Pagi': ['Budi', 'Siti', 'Ahmad'],
                        'Siang': ['Jona', 'Joni'],
                        'Malam': ['Keith', 'Kate']
                    }
                },
                ...
            ],
            'shift_names': ['Pagi', 'Siang', 'Malam'],  # Shift unik yang digunakan
            'total_records': int
        }
    """
    
    # Query semua jadwal untuk bulan ini
    first_day = datetime.date(year, month, 1)
    last_day = datetime.date(
        year,
        month,
        calendar.monthrange(year, month)[1]
    )
    
    query = Schedule.query.filter(
        Schedule.work_date >= first_day,
        Schedule.work_date <= last_day
    )
    
    if schedule_type:
        query = query.filter(Schedule.schedule_type == schedule_type)
    
    schedules = query.options(
        __import__('sqlalchemy.orm', fromlist=['joinedload']).joinedload(Schedule.user),
        __import__('sqlalchemy.orm', fromlist=['joinedload']).joinedload(Schedule.shift)
    ).all()
    
    # Group schedules by date dan shift
    schedules_by_date_shift = defaultdict(lambda: defaultdict(list))
    shift_names_set = set()
    
    for schedule in schedules:
        date_key = schedule.work_date.strftime('%d-%m')
        shift_name = schedule.shift.shift_name
        user_name = schedule.user.fullname
        
        schedules_by_date_shift[date_key][shift_name].append(user_name)
        shift_names_set.add(shift_name)
    
    # Urutkan shift berdasarkan shift_index
    shifts = Shift.query.order_by(Shift.shift_index).all()
    shift_names = [s.shift_name for s in shifts if s.shift_name in shift_names_set]
    
    # Jika tidak ada shift yang ditemukan, gunakan semua shift yang ada
    if not shift_names:
        shift_names = [s.shift_name for s in shifts]
    
    # Build schedule data
    schedule_data = []
    
    for work_date in range(1, calendar.monthrange(year, month)[1] + 1):
        current_date = datetime.date(year, month, work_date)
        date_key = current_date.strftime('%d-%m')
        day_name = DAYS_MAPPING[current_date.weekday()]
        
        shifts_data = {}
        for shift_name in shift_names:
            users = schedules_by_date_shift[date_key].get(shift_name, [])
            shifts_data[shift_name] = users
        
        # Hanya tambahkan jika ada jadwal di tanggal ini
        if any(schedules_by_date_shift[date_key].values()):
            schedule_data.append({
                'date': date_key,
                'day_name': day_name,
                'shifts': shifts_data
            })
    
    month_name = MONTHS_ID.get(month, calendar.month_name[month])
    
    return {
        'year': year,
        'month': month,
        'month_name': month_name,
        'schedule_data': schedule_data,
        'shift_names': shift_names,
        'total_records': len(schedules),
        'print_date': datetime.datetime.now().strftime('%d %B %Y'),
        'company_name': 'PT. PERUSAHAAN ANDA',
        'company_address': 'Jalan Merdeka No. 123, Jakarta, Indonesia'
    }


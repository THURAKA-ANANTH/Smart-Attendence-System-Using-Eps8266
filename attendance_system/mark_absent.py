import os
import django
import time
from django.utils import timezone
from datetime import datetime, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "attendance_system.settings")
django.setup()

from attendance.models import Timetable, Attendance, Student

GRACE_PERIOD_MINUTES = 5  # grace period

def mark_attendance_for_current_period():
    now = timezone.localtime()
    current_day = now.strftime("%A")
    periods_today = Timetable.objects.filter(day=current_day)

    for period in periods_today:
        period_start_datetime = timezone.make_aware(
            datetime.combine(now.date(), period.start_time)
        )
        grace_end_time = period_start_datetime + timedelta(minutes=GRACE_PERIOD_MINUTES)
        students = Student.objects.filter(classroom=period.classroom)

        # MARK ABSENT ONLY AFTER GRACE PERIOD
        if now > grace_end_time:
            absentees_marked = False
            for student in students:
                try:
                    # Check if attendance already exists
                    attendance = Attendance.objects.get(
                        student=student, timetable=period, date=now.date()
                    )
                    if attendance.status == "present":
                        # Student is already marked present, skip absent
                        continue
                    if not attendance.absent_flag:
                        attendance.status = "absent"
                        attendance.timestamp = period_start_datetime
                        attendance.absent_flag = True
                        attendance.save()
                        absentees_marked = True
                except Attendance.DoesNotExist:
                    # No attendance exists, mark absent
                    Attendance.objects.create(
                        student=student,
                        timetable=period,
                        date=now.date(),
                        status="absent",
                        timestamp=period_start_datetime,
                        absent_flag=True
                    )
                    absentees_marked = True

            if absentees_marked:
                print(f"Grace period over. Absentees marked for period {period} at {now.time()}")

if __name__ == "__main__":
    while True:
        mark_attendance_for_current_period()
        time.sleep(60)
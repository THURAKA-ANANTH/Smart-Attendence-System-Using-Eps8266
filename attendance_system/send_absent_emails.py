import os
import django
import time
from django.utils import timezone

# setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "attendance_system.settings")
django.setup()

from django.core.mail import send_mail
from attendance.models import Attendance

CHECK_INTERVAL = 60 * 1  # 5 minutes

def send_absent_emails():
    today = timezone.localdate()

    # Filter only absentees whose email hasn't been sent
    absent_records = Attendance.objects.filter(
        date=today, status="absent", absent_flag=True, email_sent=False
    )

    if not absent_records.exists():
        print(f"[{timezone.localtime()}] No absent students to email.")
        return

    for record in absent_records:
        student = record.student

        subject = f"Attendance Alert: You were absent on {today}"
        timetable = record.timetable

        message = f"""
        Hello {student.name},

        You were marked absent for:

        Class: {timetable.classroom.name}
        Subject: {timetable.subject.name}
        Faculty: {timetable.faculty.name}

        Period: {timetable.period_number}
        Time: {timetable.start_time.strftime('%I:%M %p')} - {timetable.end_time.strftime('%I:%M %p')}
        Date: {today}

        Please attend the next class.

        Best regards,
        Narayana Engineering College
        """
        recipient = [student.email]
        try:
            send_mail(subject, message, None, recipient, fail_silently=False)
            print(f"[{timezone.localtime()}] Email sent to {student.email}")

            # Mark email as sent to avoid duplicates
            record.email_sent = True
            record.save(update_fields=['email_sent'])

        except Exception as e:
            print(f"[{timezone.localtime()}] Failed to send email to {student.email}: {e}")

    print(f"[{timezone.localtime()}] Total emails processed: {absent_records.count()}")


if __name__ == "__main__":
    while True:
        send_absent_emails()
        time.sleep(CHECK_INTERVAL)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Faculty, Timetable, Student, Attendance, ClassRoom,Department
from datetime import date
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import requests
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail





# ---------------------- Faculty Login ----------------------
def faculty_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('faculty_classrooms')
        else:
            return render(request, 'faculty_login.html', {'error': 'Invalid credentials'})
    return render(request, 'faculty_login.html')


# ---------------------- Faculty Logout ----------------------
@login_required
def faculty_logout(request):
    logout(request)
    return redirect('faculty_login')


# ---------------------- Classroom Selection ----------------------
@login_required
def faculty_classrooms(request):
    faculty = get_object_or_404(Faculty, user=request.user)
    # Get all classrooms assigned to this faculty via timetable
    classroom_ids = Timetable.objects.filter(faculty=faculty).values_list('classroom', flat=True).distinct()
    classrooms = ClassRoom.objects.filter(id__in=classroom_ids)
    return render(request, 'faculty_classrooms.html', {'classrooms': classrooms})


# ---------------------- Subjects/Periods in a Classroom ----------------------
@login_required
def classroom_subjects(request, classroom_id):
    faculty = get_object_or_404(Faculty, user=request.user)
    timetable_entries = Timetable.objects.filter(faculty=faculty, classroom_id=classroom_id)
    classroom = timetable_entries.first().classroom if timetable_entries.exists() else None
    return render(request, 'classroom_subjects.html', {
        'timetable_entries': timetable_entries,
        'classroom': classroom
    })


# ---------------------- Mark Attendance ----------------------
@login_required
def mark_attendance(request, timetable_id):
    faculty = get_object_or_404(Faculty, user=request.user)
    timetable = get_object_or_404(Timetable, id=timetable_id, faculty=faculty)
    students = Student.objects.filter(classroom=timetable.classroom)

    if request.method == "POST":
        attendance_date = request.POST.get('date') or date.today()
        for student in students:
            # Default to 'present' if not selected
            status = request.POST.get(f'status_{student.id}', 'present')
            Attendance.objects.update_or_create(
                student=student,
                timetable=timetable,
                date=attendance_date,
                defaults={'status': status}
            )
        return redirect('faculty_classrooms')

    return render(request, 'mark_attendance.html', {
        'timetable': timetable,
        'students': students,
        'today': date.today()
    })


@api_view(['POST'])
def rfid_scan(request):
    """
    API for ESP8266 to send RFID scan
    Request JSON:
    {
        "rfid_uid": "123456789"
    }
    """
    rfid_uid = request.data.get('rfid_uid')
    if not rfid_uid:
        return Response({"status": "error", "message": "rfid_uid missing", "color": "red"}, status=400)

    # Check if student exists
    try:
        student = Student.objects.get(rfid_uid=rfid_uid)
    except Student.DoesNotExist:
        return Response({"status": "error", "message": "RFID not assigned to any student", "color": "red"}, status=404)

    if not student.classroom:
        return Response({"status": "error", "message": "Student has no classroom assigned", "color": "red"}, status=400)

    now = timezone.localtime()
    current_day = now.strftime("%A")
    buffer = timedelta(minutes=5)

    # Find active period for classroom
    timetable = Timetable.objects.filter(
        classroom=student.classroom,
        day=current_day,
        start_time__lte=(now + buffer).time(),
        end_time__gte=(now - buffer).time()
    ).first()

    if not timetable:
        return Response({"status": "error", "message": "No active period now", "color": "red"}, status=400)

    # Check if attendance already exists
    attendance_exists = Attendance.objects.filter(
        student=student,
        timetable=timetable,
        date=now.date()
    ).exists()

    if attendance_exists:
        return Response({
            "status": "already_marked",
            "message": "Attendance already marked",
            "color": "yellow",
            "student": student.name,
            "classroom": student.classroom.name,
            "period": timetable.period_number
        })

    # Mark attendance
    Attendance.objects.create(
        student=student,
        timetable=timetable,
        date=now.date(),
        status="present",
        timestamp=now
    )

    return Response({
        "status": "success",
        "message": "Attendance marked successfully",
        "color": "green",
        "student": student.name,
        "classroom": student.classroom.name,
        "period": timetable.period_number
    })








@api_view(['POST'])
def capture_rfid(request):
    """
    Capture RFID UID and return student details if mapped.
    If UID not mapped, create a dummy student for admin to manage later.
    """
    uid = request.data.get("rfid_uid")
    if not uid:
        return Response({"error": "RFID UID missing"}, status=status.HTTP_400_BAD_REQUEST)

    # Try to get or create a student
    student, created = Student.objects.get_or_create(
        rfid_uid=uid,
        defaults={
            "name": f"New Student {uid[-4:]}",  # dummy name using last 4 digits
            "email": f"{uid[-4:]}@example.com",  # dummy email
            "roll_number": f"RN{uid[-4:]}",  # dummy roll number
            "classroom": None  # admin can assign later
        }
    )

    # If created, mapped is False (new dummy), else True
    return Response({
        "rfid_uid": uid,
        "mapped": not created,
        "name": student.name,
        "email": student.email,
        "roll_number": student.roll_number,
        "classroom": str(student.classroom) if student.classroom else None,
        "color": "green" if not created else "green"  # keep green for scanned students
    })
def rfid_capture_view(request):
    """
    Render the RFID capture frontend page
    """
    return render(request, 'rfid_capture.html')


# @api_view(['POST'])
# def rfid_scan(request):
#     rfid_uid = request.data.get("rfid_uid")
#     try:
#         student = get_object_or_404(Student, rfid_uid=rfid_uid)

#         # Find current timetable (if any)
#         current_time = timezone.now()
#         timetable = Timetable.objects.filter(
#             classroom=student.classroom,
#             day=current_time.strftime("%A"),
#             start_time__lte=current_time.time(),
#             end_time__gte=current_time.time()
#         ).first()

#         # Save attendance
#         if timetable:
#             Attendance.objects.update_or_create(
#                 student=student,
#                 timetable=timetable,
#                 date=timezone.localdate(current_time),
#                 defaults={"status": "present", "timestamp": current_time}
#             )

#         # Prepare minimal data for UI
#         student_data = {
#             "rfid_uid": student.rfid_uid,
#             "name": student.name,
#             "roll_number": student.roll_number,
#             "classroom": str(student.classroom)
#         }

#         # Broadcast via Channels
#         channel_layer = get_channel_layer()
#         async_to_sync(channel_layer.group_send)(
#             "attendance",
#             {
#                 "type": "student.scan",
#                 "message": student_data
#             }
#         )

#         return Response({"status": "success", "student": student_data})

#     except Student.DoesNotExist:
#         return Response({"status": "error", "message": "Student UID not found"}, status=404)


# views.py


def send_absent_emails(request):
    today = timezone.localdate()
    
    # get all attendance records for today with status "absent"
    absent_records = Attendance.objects.filter(date=today, status="absent")

    for record in absent_records:
        student = record.student
        subject = f"Attendance Alert: You were absent on {today}"
        message = f"Hello {student.name},\n\nYou were marked absent for {record.timetable} on {today}.\nPlease make sure to attend the next class.\n\nBest regards,\nYour School"
        recipient = [student.email]

        send_mail(
            subject,
            message,
            None,  # from email (uses DEFAULT_FROM_EMAIL)
            recipient,
            fail_silently=False
        )

    return render(request, "attendance/email_sent.html", {"count": absent_records.count()})
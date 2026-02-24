from django.urls import path
from . import views  # this is correct, because views.py is in the same app

urlpatterns = [
    path('faculty/login/', views.faculty_login, name='faculty_login'),
    path('faculty/logout/', views.faculty_logout, name='faculty_logout'),
    path('faculty/classrooms/', views.faculty_classrooms, name='faculty_classrooms'),
    path('faculty/classroom/<int:classroom_id>/subjects/', views.classroom_subjects, name='classroom_subjects'),
    path('faculty/attendance/<int:timetable_id>/', views.mark_attendance, name='mark_attendance'),
    path('rfid_scan/', views.rfid_scan, name='rfid_scan'),
    path('api/capture_rfid/', views.capture_rfid, name='capture_rfid'),
    path('rfid_capture/', views.rfid_capture_view, name='rfid_capture'),
    path('send-absent-emails/', views.send_absent_emails, name="send_absent_emails"),
]
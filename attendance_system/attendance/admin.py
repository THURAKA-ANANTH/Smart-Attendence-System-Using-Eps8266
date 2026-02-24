from django.contrib import admin
from django import forms
from .models import *

# ----------------------------
# Custom form for Timetable
# ----------------------------
class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = "__all__"
        widgets = {
            "start_time": forms.TimeInput(
                format='%H:%M',
                attrs={'type': 'time', 'class': 'vTimeField'}  # shows browser time picker
            ),
            "end_time": forms.TimeInput(
                format='%H:%M',
                attrs={'type': 'time', 'class': 'vTimeField'}
            ),
        }

# ----------------------------
# Timetable admin using custom form
# ----------------------------
@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    form = TimetableForm
    list_display = ['classroom', 'day', 'period_number', 'start_time', 'end_time']

# ----------------------------
# Other admin registrations
# ----------------------------
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "roll_number", "classroom", "rfid_uid")

admin.site.register(Department)
admin.site.register(ClassRoom)
admin.site.register(Faculty)
admin.site.register(Subject)
admin.site.register(Attendance)
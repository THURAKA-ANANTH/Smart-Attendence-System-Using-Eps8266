from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


# ----------------------------
# DEPARTMENT
# ----------------------------
class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# ----------------------------
# CLASS / SECTION
# Example: CSE-A, ECE-B
# ----------------------------
class ClassRoom(models.Model):
    name = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    year = models.IntegerField()  # 1st year, 2nd year etc

    def __str__(self):
        return f"{self.name} - Year {self.year}"


# ----------------------------
# FACULTY / TEACHER
# ----------------------------
class Faculty(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # login user
    name = models.CharField(max_length=100)

    # Use null=True temporarily to avoid migration errors if DB already has data
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,  # <- set temporarily to allow existing rows
        blank=True
    )

    def __str__(self):
        return self.name


# ----------------------------
# SUBJECT
# ----------------------------
class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


# ----------------------------
# STUDENT
# ----------------------------
class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    roll_number = models.CharField(max_length=50)
    rfid_uid = models.CharField(max_length=50, unique=True)
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True  # allows forms to leave it empty
    )

    def __str__(self):
        return f"{self.name} ({self.roll_number})"


# ----------------------------
# REAL TIMETABLE (PERIOD BASED)
# ----------------------------


class Timetable(models.Model):
    DAY_CHOICES = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]

    classroom = models.ForeignKey('ClassRoom', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    faculty = models.ForeignKey('Faculty', on_delete=models.CASCADE)

    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    period_number = models.IntegerField(
        default=1,
        help_text="Enter the period number (e.g., 1 for first period, 2 for second, etc.)"
    )
    start_time = models.TimeField(help_text="Start time of the period (HH:MM)")
    end_time = models.TimeField(help_text="End time of the period (HH:MM)")

    class Meta:
        unique_together = ("classroom", "day", "period_number")
        ordering = ["day", "start_time"]

    def __str__(self):
        return f"{self.classroom} - Period {self.period_number} - {self.day}"

    def clean(self):
        """Prevent overlapping periods for the same classroom and day."""
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

        # Find any overlapping periods in the same classroom and day
        overlapping_periods = Timetable.objects.filter(
            classroom=self.classroom,
            day=self.day
        ).exclude(pk=self.pk)  # exclude self when updating

        for period in overlapping_periods:
            # Overlap occurs if start < other.end AND end > other.start
            if self.start_time < period.end_time and self.end_time > period.start_time:
                raise ValidationError(
                    f"Time overlaps with period {period.period_number} "
                    f"({period.start_time.strftime('%H:%M')} - {period.end_time.strftime('%H:%M')})"
                )

    def save(self, *args, **kwargs):
        self.clean()  # validate before saving
        super().save(*args, **kwargs)

# ----------------------------
# ATTENDANCE (SUBJECT WISE)
# ----------------------------
from django.db import models
from django.utils import timezone

class Attendance(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
    ]

    student = models.ForeignKey("Student", on_delete=models.CASCADE)
    timetable = models.ForeignKey("Timetable", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    date = models.DateField(editable=False)  # derived from timestamp
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="present"
    )
    absent_flag = models.BooleanField(default=False)  # Optional: track if absent is already processed
    email_sent = models.BooleanField(default=False)  # NEW FIELD

    class Meta:
        unique_together = ("student", "timetable", "date")
        ordering = ["-date", "-timestamp"]

    def save(self, *args, **kwargs):
        # ensure date always matches timestamp
        if self.timestamp:
            self.date = self.timestamp.date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.status} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
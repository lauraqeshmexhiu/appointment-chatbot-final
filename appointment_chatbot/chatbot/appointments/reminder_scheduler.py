from apscheduler.schedulers.background import BackgroundScheduler
from django.core.mail import send_mail
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from .models import Appointment

def send_reminder(appointment):
    subject = f"Reminder: Appointment with Dr. {appointment.doctor.name}"
    message = (
        f"Hello {appointment.user_name},\n\n"
        f"This is a reminder that you have an appointment with Dr. {appointment.doctor.name} "
        f"on {appointment.date.strftime('%A, %d %B %Y')} at {appointment.time.strftime('%I:%M %p')}.\n"
        f"Please be on time. Thank you!"
    )
    send_mail(subject, message, None, [appointment.email])

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_reminders, 'interval', minutes=1)
    scheduler.start()


def check_and_send_reminders():
    now = make_aware(datetime.now())
    reminder_time = now + timedelta(hours=24)

    # Round seconds and microseconds
    reminder_time = reminder_time.replace(second=0, microsecond=0)

    print(f"⏰ Looking for appointment at {reminder_time}")

    upcoming_appointments = Appointment.objects.filter(
        date=reminder_time.date(),
        time=reminder_time.time()
    )

    print(f"📧 Reminders to send: {len(upcoming_appointments)}")

    for appt in upcoming_appointments:
        print(f"📨 Sending reminder to: {appt.email} for {appt.user_name}")
        send_reminder(appt)

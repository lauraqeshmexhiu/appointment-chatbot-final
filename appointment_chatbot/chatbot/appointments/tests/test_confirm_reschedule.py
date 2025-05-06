import os
from dotenv import load_dotenv
from django.test import TestCase, Client
from django.urls import reverse
from appointments.models import Doctor, Appointment, DoctorAvailability
from datetime import date, time
import json

class ConfirmRescheduleTestCase(TestCase):
    def setUp(self):
        load_dotenv()
        self.secret = os.getenv("DIALOGFLOW_SECRET")
        self.doctor = Doctor.objects.create(name="Dr. Jack", specialization="General Practitioner")
        DoctorAvailability.objects.create(
            doctor=self.doctor,
            day_of_week="Thursday",
            start_time=time(9),
            end_time=time(17)
        )

        self.appointment = Appointment.objects.create(
            user_name="Laura",
            symptoms="headache",
            date=date(2025, 4, 16),
            time="10:00:00",
            doctor=self.doctor
        )

        self.client = Client()
        self.url = reverse("dialogflow_webhook")

    def test_confirm_reschedule(self):
        """Test if an appointment is successfully rescheduled after user confirmation."""
        payload = {
            "queryResult": {
                "intent": {"displayName": "Confirm reschedule"},
                "outputContexts": [
                    {
                        "name": "projects/project-id/agent/sessions/session-id/contexts/awaiting_reschedule_confirmation",
                        "parameters": {
                            "person": "Laura",
                            "appointment_id": self.appointment.id,
                            "new_date": "2025-04-18",
                            "new_time": "14:00:00"
                        }
                    }
                ]
            }
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            **{"HTTP_X_DIALOGFLOW_SECRET": self.secret}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("has been rescheduled to", response.json()["fulfillmentText"].lower())

        updated = Appointment.objects.get(id=self.appointment.id)
        self.assertEqual(str(updated.date), "2025-04-18")
        self.assertEqual(updated.time.strftime("%H:%M:%S"), "14:00:00")

import os
from dotenv import load_dotenv
from django.test import TestCase, Client
from django.urls import reverse
from appointments.models import Doctor, Appointment, DoctorAvailability
from datetime import date, time
import json

class RescheduleAppointmentTestCase(TestCase):
    def setUp(self):
        load_dotenv()
        self.secret = os.getenv("DIALOGFLOW_SECRET")

        self.doctor = Doctor.objects.create(name="Dr. Jack", specialization="General Practitioner")
        DoctorAvailability.objects.create(
            doctor=self.doctor, day_of_week="Wednesday", start_time=time(9), end_time=time(17)
        )

        Appointment.objects.create(
            user_name="Laura",
            symptoms="fever",
            date=date(2025, 4, 16),
            time="10:00:00",
            doctor=self.doctor
        )

        self.client = Client()
        self.url = reverse("dialogflow_webhook")

    def test_reschedule_appointment(self):
        """Test if the system offers a new slot when the user wants to reschedule."""
        payload = {
            "queryResult": {
                "intent": {"displayName": "Reschedule Appointment"},
                "parameters": {"person": [{"name": "Laura"}]}
            }
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            **{"HTTP_X_DIALOGFLOW_SECRET": self.secret}
        )
        
        print("Fulfillment:", response.json()["fulfillmentText"])
        self.assertEqual(response.status_code, 200)
        self.assertIn("next available slot", response.json()["fulfillmentText"].lower())

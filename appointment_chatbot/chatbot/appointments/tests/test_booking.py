import os
import json
from django.test import TestCase, Client
from django.urls import reverse
from dotenv import load_dotenv
from appointments.models import Doctor, DoctorAvailability
from datetime import time

class BookingTestCase(TestCase):
    def setUp(self):
        load_dotenv()
        self.secret = os.getenv("DIALOGFLOW_SECRET")
        self.client = Client()
        self.url = reverse("dialogflow_webhook")

        self.doctor = Doctor.objects.create(name="Dr. Smith", specialization="General Practitioner")
        DoctorAvailability.objects.create(doctor=self.doctor, day_of_week="Monday", start_time=time(9, 0), end_time=time(17, 0))

    def test_book_appointment_with_email(self):
        payload = {
            "queryResult": {
                "intent": {"displayName": "capture symptoms"},
                "parameters": {
                    "Symptoms": ["fever", "chills"]
                },
                "queryText": "I have a fever and chills",
                "outputContexts": [
                    {
                        "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_symptoms",
                        "lifespanCount": 3,
                        "parameters": {
                            "person": "Alice",
                            "email": "alice@example.com"
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
        self.assertIn("fulfillmentText", response.json())
        self.assertIn("appointment_confirm", json.dumps(response.json()))

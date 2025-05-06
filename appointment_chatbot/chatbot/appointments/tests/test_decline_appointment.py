import os
import json
from django.test import TestCase, Client
from django.urls import reverse
from appointments.models import Doctor, DoctorAvailability, Appointment
from datetime import date, time
from dotenv import load_dotenv

class DeclineAppointmentSuggestionTestCase(TestCase):
    def setUp(self):
        load_dotenv()
        self.secret = os.getenv("DIALOGFLOW_SECRET")
        self.client = Client()
        self.url = reverse("dialogflow_webhook")
        self.doctor = Doctor.objects.create(name="Dr. Jack", specialization="General Practitioner")
        DoctorAvailability.objects.create(
            doctor=self.doctor,
            day_of_week="Wednesday",
            start_time=time(9),
            end_time=time(17)
        )

    def test_decline_appointment_suggests_new_time(self):
        """Tests that declining an appointment suggestion leads to a new alternative suggestion."""
        payload = {
            "queryResult": {
                "intent": {"displayName": "Decline appointment time"},
                "outputContexts": [
                    {
                        "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/appointment_confirm",
                        "lifespanCount": 5,
                        "parameters": {
                            "person": "Alice",
                            "doctor": "Dr. Jack",
                            "specialization": "General Practitioner",
                            "symptoms": "fever",
                            "suggested_date": "2025-06-10",
                            "suggested_time": "10:00:00",
                            "previous_attempts": []
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
        self.assertIn("how about", response.json()["fulfillmentText"].lower())
        self.assertIn("dr. jack", response.json()["fulfillmentText"].lower())

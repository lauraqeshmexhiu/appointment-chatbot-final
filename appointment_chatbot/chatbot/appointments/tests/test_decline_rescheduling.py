import os
import json
from django.test import TestCase, Client
from django.urls import reverse
from dotenv import load_dotenv
from appointments.models import Doctor, DoctorAvailability
from datetime import time

class DeclineReschedulingTestCase(TestCase):
    def setUp(self):
        load_dotenv()
        self.secret = os.getenv("DIALOGFLOW_SECRET")
        self.doctor = Doctor.objects.create(name="Dr. Jack", specialization="General Practitioner")
        DoctorAvailability.objects.create(
            doctor=self.doctor, day_of_week="Tuesday", start_time=time(9), end_time=time(17)
        )

        self.client = Client()
        self.url = reverse("dialogflow_webhook")

    def test_decline_rescheduling_suggests_new_slot(self):
        payload = {
            "queryResult": {
                "intent": {"displayName": "Decline rescheduling"},
                "outputContexts": [
                    {
                        "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_reschedule_confirmation",
                        "lifespanCount": 3,
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

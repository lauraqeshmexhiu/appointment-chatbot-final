from django.test import TestCase, Client
from django.urls import reverse
from appointments.models import Doctor, DoctorAvailability, Appointment
from datetime import time, date
import json
import os
from dotenv import load_dotenv

class CancelAppointmentTestCase(TestCase):
    def setUp(self):
        load_dotenv()  
        self.secret = os.getenv("DIALOGFLOW_SECRET") 
        self.doctor = Doctor.objects.create(name="Dr. Jack", specialization="General Practitioner")
        DoctorAvailability.objects.create(
            doctor=self.doctor,
            day_of_week="Monday",
            start_time=time(9),
            end_time=time(17)
        )
        self.appointment = Appointment.objects.create(
            user_name="Laura",
            symptoms="fever",
            date=date.today(),
            time="10:00:00",
            doctor=self.doctor
        )

        self.client = Client()
        self.url = reverse("dialogflow_webhook")

    def test_cancel_single_appointment(self):
        payload = {
            "queryResult": {
                "intent": {"displayName": "Cancel appointment"},
                "parameters": {
                    "person": [{"name": "Laura"}]
                }
            }
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            **{"HTTP_X_DIALOGFLOW_SECRET": self.secret}
        )

        print("Response:", response.json()["fulfillmentText"])

        self.assertEqual(response.status_code, 200)
        self.assertIn("Dr. Jack", response.json()["fulfillmentText"])
        self.assertFalse(Appointment.objects.filter(user_name="Laura").exists())

import os
import json
from django.test import TestCase, Client
from django.urls import reverse
from dotenv import load_dotenv

class MissingSymptomsTestCase(TestCase):
    def setUp(self):
        load_dotenv()
        self.secret = os.getenv("DIALOGFLOW_SECRET")
        self.client = Client()
        self.url = reverse("dialogflow_webhook")

    def test_booking_without_symptoms_prompts_for_symptoms(self):
        payload = {
            "queryResult": {
                "intent": {"displayName": "capture symptoms"},
                "parameters": {
                    "Symptoms": [] 
                },
                "queryText": "I need to see a doctor",
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
        print("ACTUAL RESPONSE:", response.json()["fulfillmentText"])
        self.assertIn("symptoms", response.json()["fulfillmentText"].lower())


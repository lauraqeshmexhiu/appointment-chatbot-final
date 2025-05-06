import os
import json
from django.test import TestCase, Client
from django.urls import reverse
from dotenv import load_dotenv

class MissingEmailTestCase(TestCase):
    def setUp(self):
        load_dotenv() 
        self.secret = os.getenv("DIALOGFLOW_SECRET")
        self.client = Client()
        self.url = reverse("dialogflow_webhook")

    def test_booking_without_email_prompts_for_email(self):
        payload = {
            "queryResult": {
                "intent": {"displayName": "capture symptoms"},
                "parameters": {
                    "Symptoms": ["chills"]  
                },
                "queryText": "I have chills",
                "outputContexts": [
                    {
                        "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_symptoms",
                        "lifespanCount": 3,
                        "parameters": {
                            "person": "Alice"
                            # No email provided
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

        print("FulfillmentText:", response.json()["fulfillmentText"])
        self.assertEqual(response.status_code, 200)
        self.assertIn("your email", response.json()["fulfillmentText"].lower())

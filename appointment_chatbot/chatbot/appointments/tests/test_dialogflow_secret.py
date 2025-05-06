import os
import json
from django.test import TestCase, Client
from django.urls import reverse
from dotenv import load_dotenv

class DialogflowSecretTestCase(TestCase):
    def setUp(self):
        load_dotenv()  
        self.secret = os.getenv("DIALOGFLOW_SECRET")
        self.client = Client()
        self.url = reverse("dialogflow_webhook")
        self.payload = {
            "queryResult": {
                "intent": {"displayName": "Test intent"},
                "parameters": {}
            }
        }

    def test_valid_secret(self):
        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            **{"HTTP_X_DIALOGFLOW_SECRET": self.secret}  
        )
        self.assertNotEqual(response.status_code, 403)

    def test_invalid_secret(self):
        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            **{"HTTP_X_DIALOGFLOW_SECRET": "wrongsecret"}
        )
        self.assertEqual(response.status_code, 403)

    def test_missing_secret(self):
        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

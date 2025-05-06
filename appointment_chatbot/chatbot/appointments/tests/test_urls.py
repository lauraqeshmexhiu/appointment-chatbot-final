from django.test import SimpleTestCase
from django.urls import reverse, resolve
from appointments.views import dialogflow_webhook


class TestUrls(SimpleTestCase):
    def test_webhook_url_is_resolved(self):
        url = reverse('dialogflow_webhook')
        self.assertEqual(resolve(url).func, dialogflow_webhook)

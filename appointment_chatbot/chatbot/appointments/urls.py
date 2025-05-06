from django.urls import path
from .views import dialogflow_webhook


urlpatterns = [
    path("dialogflow/", dialogflow_webhook, name="dialogflow_webhook"),
]

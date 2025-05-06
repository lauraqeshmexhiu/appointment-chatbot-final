# appointment-chatbot-final
Install ngrok (if not already installed)
You can install ngrok by visiting: https://ngrok.com/download
After installing, run:
ngrok http https://localhost:8000

A preconfigured Dialogflow agent is included in this project (`appointment.zip`).

To use it:

1. Go to [Dialogflow Console](https://dialogflow.cloud.google.com/) and create a new agent.
2. Navigate to Agent Settings (⚙️ icon) > Export and Import > Import from ZIP.
3. Upload the provided `appointment-agent.zip`.
4. Go to Fulfillment > Webhook and:
   - Enable the webhook.
   - Set the URL to your `ngrok` URL followed by `/dialogflow/`, e.g:
   - Forwarding -> https://ngrokid.app 
     https://your-ngrok-id.ngrok.io/api/dialogflow/
   - Add the following header:
     Key: X-Dialogflow-Secret
     Value: <use the value from your .env file>
   - Then go to settings.py and in the allowed hosts update the allowed hosts with the ngrok id but this time without the full link just like this :"5fd4-81-111-240-39.ngrok-free.app"

Backend set up
   - python -m venv venv
   - venv\Scripts\activate
   - cd appointment_chatbot
   - pip install -r requirements.txt
   - pip install django-extensions werkzeug
   - python manage.py runserver_plus --cert-file cert.pem --key-file key.pem
     
Front end set up
- npm install
- npm run serve



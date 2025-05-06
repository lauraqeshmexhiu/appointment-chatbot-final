<template>
  <div class="page-wrapper">
    <div class="header">
      <h2>💬 Appointment Chatbot</h2>
      <p class="subtext">Book, reschedule, or cancel your doctor’s appointments easily.</p>
      <p class="helper-text">Try saying: <strong>"Book an appointment, I have x, y, z symptoms"</strong></p>
    </div>

    <div class="disclaimer">
      ⚠️ <strong>Important:</strong> This chatbot is for booking routine appointments only.  
      If you have a medical emergency, call <strong>999</strong> or visit your nearest <strong>A&E</strong>.  
      For non-emergencies, call <strong>NHS 111</strong>.
    </div>
    <div class="chat-wrapper">
      <iframe
        allow="microphone;"
        src="https://console.dialogflow.com/api-client/demo/embedded/f6d14bfc-a0b8-4763-9fe4-ede562fdf1e3"
        class="chatbot-frame"
      ></iframe>
    </div>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: 'Segoe UI', sans-serif;
  background: linear-gradient(to right, #f8f9fa, #f5f5f5);
}

.page-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  min-height: 100vh;
  animation: fadeIn 0.8s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.header {
  text-align: center;
  margin-bottom: 20px;
  max-width: 800px;
  width: 100%;
}

.header h2 {
  font-size: 2.8rem;
  font-weight: 700;
  margin-bottom: 10px;
  color: #0a2a43;
}

.subtext {
  font-size: 1.25rem;
  color: #5f6368;
  margin-bottom: 12px;
}

.helper-text {
  font-size: 1.05rem;
  color: #0a2a43;
  margin-bottom: 10px;
  text-align: center;
}


.disclaimer {
  font-size: 1.05rem;
  color: #8b0000;
  background-color: #fff3f3;
  border-left: 4px solid #e57373;
  padding: 16px 22px;
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  max-width: 800px;
  width: 100%;
  text-align: left;
  line-height: 1.6;
  margin-top: 20px;
  margin-bottom: 40px;
}

.chat-wrapper {
  background: white;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  border-radius: 16px;
  overflow: hidden;
  width: 95%;
  max-width: 1800px;
  height: 950px;
  transition: box-shadow 0.3s ease;
}

.chat-wrapper:hover {
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
}

.chatbot-frame {
  width: 100%;
  height: 100%;
  border: none;
}
</style>

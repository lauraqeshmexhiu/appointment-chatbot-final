
import json
import os
import re 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Appointment, Doctor, DoctorAvailability
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponseForbidden
from dotenv import load_dotenv


# Mapping Symptoms to Doctors
DOCTOR_MAPPING = {
    "fever": "General Practitioner",
    "rash": "Dermatologist",
    "headache": "Neurologist",
}

SYMPTOM_SYNONYMS = {
    "fever": ["high temperature", "feel hot", "feeling hot", "chills"],
    "rash": ["spots", "red skin", "itchy skin"],
    "headache": ["headache", "head pain", "migraine", "pounding head", "aching head"]
}


@csrf_exempt
def dialogflow_webhook(request): 
    load_dotenv()
    received_secret = request.headers.get("X-Dialogflow-Secret")
    expected_secret = os.getenv("DIALOGFLOW_SECRET")

    if received_secret != expected_secret:
       return HttpResponseForbidden("Forbidden: Invalid secret")

    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests allowed"}, status=400)

    try:
        data = json.loads(request.body)
        parameters = data.get("queryResult", {}).get("parameters", {})
        output_contexts = data.get("queryResult", {}).get("outputContexts", [])
        intent_name = data.get("queryResult", {}).get("intent", {}).get("displayName", "")
        query_text = data.get("queryResult", {}).get("queryText", "") 

        if intent_name == "capture symptoms":
            ctx_params = extract_context_params(output_contexts, "awaiting_symptoms")
            stored_person = ctx_params.get("person", "")
            stored_email = ctx_params.get("email", "")

            if not stored_person:
                return JsonResponse({"fulfillmentText": "I need to know who the appointment is for. What is your name?"})

            normalised_symptoms, user_symptoms_by_condition = extract_symptoms(parameters, query_text)

            if not normalised_symptoms:
                return JsonResponse({"fulfillmentText": "I didn't catch your symptoms. Can you please repeat them?"})

            return process_appointment(stored_person, normalised_symptoms, user_symptoms_by_condition, stored_email)


        if intent_name == "Book appointment":
            person = extract_person(parameters)
            normalised_symptoms, user_symptoms_by_condition = extract_symptoms(parameters, query_text)
            return process_appointment(person, normalised_symptoms, user_symptoms_by_condition)

        if intent_name == "Capture email":
            context_data = extract_context_params(output_contexts, "awaiting_email")
            person = context_data.get("person", "")
            symptoms = context_data.get("symptoms", [])
            user_symptoms_by_condition = context_data.get("user_symptoms", {})

            email = parameters.get("email")
            return process_appointment(person, symptoms, user_symptoms_by_condition, email)

        if intent_name == "Appointment confirm":
            return confirm_appointment(output_contexts)

        if intent_name == "Cancel appointment":
            return cancel_appointment(output_contexts, parameters)

        if intent_name == "Confirm cancel appointment":
            return confirm_cancel_appointment(output_contexts, parameters)

        if intent_name == "Reschedule Appointment":
            return reschedule_appointment(output_contexts, parameters)

        if intent_name == "Confirm reschedule":
            context_names = [ctx["name"] for ctx in output_contexts]

            if any("awaiting_reschedule_confirmation" in ctx for ctx in context_names) and not parameters.get("number"):
                return confirm_reschedule_appointment(output_contexts, parameters)

            if any("awaiting_reschedule_selection" in ctx for ctx in context_names):
                return confirm_reschedule_selection(output_contexts, parameters)

        if intent_name == "Decline appointment time":
            return suggest_alternative_time(output_contexts)

        if intent_name == "Decline rescheduling":
            return suggest_alternative_time(output_contexts)

        return JsonResponse({"fulfillmentText": "I didn't understand your request."})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)


def extract_person(parameters):
    """Extracts the person's name correctly from Dialogflow request parameters."""
    person = parameters.get("person", [])

    if isinstance(person, list) and person:
        # Ensure we extract only the name field from the list of dicts
        if isinstance(person[0], dict) and "name" in person[0]:
            return str(person[0]["name"]).strip()

    elif isinstance(person, dict):
        return str(person.get("name", "")).strip()

    return str(person).strip() 

def extract_symptoms(parameters, query_text=None):
    normalised = set()
    user_symptoms_by_condition = {}
    seen_phrases = set()

    # Pull symptoms from Dialogflow parameters
    raw_symptoms = parameters.get("Symptoms") or parameters.get("symptoms") or []
    if isinstance(raw_symptoms, str):
        raw_symptoms = [raw_symptoms]
    for s in raw_symptoms:
        lower = s.lower().strip()
        if lower in seen_phrases:
            continue
        seen_phrases.add(lower)
        for canonical, synonyms in SYMPTOM_SYNONYMS.items():
            if lower in synonyms:
                normalised.add(canonical)
                user_symptoms_by_condition.setdefault(canonical, []).append(lower)
                break

    # Fallback: Match whole words in raw user query
    if query_text:
        lowered_query = query_text.lower()
        for canonical, synonyms in SYMPTOM_SYNONYMS.items():
            for synonym in synonyms:
                # Match whole words only
                   if re.search(r'\b' + re.escape(synonym) + r'\b', lowered_query) and synonym not in seen_phrases:
                    seen_phrases.add(synonym)
                    normalised.add(canonical)
                    user_symptoms_by_condition.setdefault(canonical, []).append(synonym)

    return list(normalised), user_symptoms_by_condition

def determine_best_doctor(user_symptoms_by_condition):
    """
    Finds the best doctor based on how many symptom phrases the user gave 
    for each condition (i.e. weight by len(expressions)).
    """
    doctor_scores = {}
    for condition, expressions in user_symptoms_by_condition.items():
        matched_specialty = DOCTOR_MAPPING.get(condition, "General Practitioner")
        # add one point per reported phrase
        doctor_scores[matched_specialty] = doctor_scores.get(matched_specialty, 0) + len(expressions)

    # pick the specialty with the highest total
    if not doctor_scores:
        specialisation = "General Practitioner"
    else:
        specialisation = max(doctor_scores, key=doctor_scores.get)

    doctor_obj = Doctor.objects.filter(specialization=specialisation).first()
    return doctor_obj, specialisation

 
def find_next_available_slot(doctor, exclude_date=None, exclude_time=None, excluded_slots=None):
    today = datetime.now().date()
    now = datetime.now()

    if excluded_slots is None:
        excluded_slots = set()

    availability = DoctorAvailability.objects.filter(doctor=doctor)

    for i in range(14):  # Look ahead up to 2 weeks
        check_date = today + timedelta(days=i)
        day_name = check_date.strftime("%A")
        daily_slots = availability.filter(day_of_week=day_name)

        valid_slots = []

        for slot in daily_slots:
            start_dt = datetime.combine(check_date, slot.start_time)
            end_dt = datetime.combine(check_date, slot.end_time)

            current_time = start_dt
            if check_date == today and now > current_time:
                current_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

            while current_time + timedelta(hours=1) <= end_dt:
                slot_time = current_time.strftime("%H:%M:%S")
                slot_date = current_time.strftime("%Y-%m-%d")

                if (slot_date, slot_time) in excluded_slots or (exclude_date == slot_date and exclude_time == slot_time):
                    current_time += timedelta(hours=1)
                    continue

                if not Appointment.objects.filter(doctor=doctor, date=slot_date, time=slot_time).exists():
                    valid_slots.append((slot_date, slot_time))

                current_time += timedelta(hours=1)

        # Return the first unbooked & unexcluded slot for this date
        if valid_slots:
            return valid_slots[0]

    return None, None


def process_appointment(person, symptoms, user_symptoms_by_condition, email=None):
    if not person:
        return JsonResponse({
            "fulfillmentText": "I need to know your name before I can book an appointment. What is your name?",
            "outputContexts": [
                {
                    "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_name",
                    "lifespanCount": 3
                }
            ]
        })

    if not email:
        return JsonResponse({
            "fulfillmentText": f"Thanks {person}. Before we continue, could you tell me your email address?",
            "outputContexts": [
                {
                    "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_email",
                    "lifespanCount": 3,
                    "parameters": {
                        "person": person,
                        "symptoms": symptoms,
                        "user_symptoms": user_symptoms_by_condition
                    }
                }
            ]
        })

    if not symptoms:
        return JsonResponse({
            "fulfillmentText": f"Hi {person}, I need to know your symptoms to book the right doctor for you. Could you please tell me what symptoms you're experiencing?",
            "outputContexts": [
                {
                    "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_symptoms",
                    "lifespanCount": 3,
                    "parameters": {"person": person}
                }
            ]
        })

    doctor_obj, specialisation = determine_best_doctor(user_symptoms_by_condition)

    if not doctor_obj:
        return JsonResponse({"fulfillmentText": f"Sorry, no available doctor for {specialisation}."})

    suggested_date, suggested_time = find_next_available_slot(doctor_obj)

    if not suggested_date:
        return JsonResponse({"fulfillmentText": f"Sorry, Dr. {doctor_obj.name} ({specialisation}) is fully booked for the next 2 weeks."})

    symptom_descriptions = []
    for condition in symptoms:
        expressions = user_symptoms_by_condition.get(condition, [])
        if not expressions:
            continue
        if len(expressions) == 1:
            desc = expressions[0]
        else:
            desc = ", ".join(expressions[:-1]) + f", and {expressions[-1]}"
        symptom_descriptions.append(desc)

    mentioned_text = ", ".join(symptom_descriptions)
    condition_text = (
        f"it sounds like you may have a {symptoms[0]}" if len(symptoms) == 1
        else "it sounds like you may have " + ", ".join(symptoms[:-1]) + f", and {symptoms[-1]}"
    )

    formatted_dt = datetime.strptime(f"{suggested_date} {suggested_time}", "%Y-%m-%d %H:%M:%S")
    formatted_time_text = formatted_dt.strftime("%A, %d %B %Y at %I:%M %p")

    return JsonResponse({
        "fulfillmentText": (
            f"You mentioned {mentioned_text}. Based on that, {condition_text}. "
            f"I recommend Dr. {doctor_obj.name} ({specialisation}). "
            f"The next available appointment is on {formatted_time_text}. "
            f"Shall I confirm this appointment for {person}?"
        ),
        "outputContexts": [
            {
                "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/appointment_confirm",
                "lifespanCount": 5,
                "parameters": {
                    "person": person,
                    "email": email,
                    "doctor": doctor_obj.name,
                    "specialization": specialisation,
                    "user_symptoms_text": ', '.join(
                        phrase
                        for phrases in user_symptoms_by_condition.values()
                        for phrase in phrases
                    ),
                    "user_symptoms": user_symptoms_by_condition,
                    "suggested_date": suggested_date,
                    "suggested_time": suggested_time
                }
            }
        ]
    })

def confirm_appointment(output_contexts):
    """Confirms the appointment and stores it in the database."""
    
    stored_params = extract_context_params(output_contexts, "appointment_confirm")
    
    if not stored_params:
        return JsonResponse({"fulfillmentText": "I couldn't confirm your appointment. Please try again."})

    doctor_obj = Doctor.objects.filter(name=stored_params["doctor"]).first()

    if not doctor_obj:
        return JsonResponse({"fulfillmentText": f"Error: Doctor {stored_params['doctor']} not found in the system."})
    
    symptoms_text = stored_params.get("user_symptoms_text", stored_params.get("symptoms", ""))

    Appointment.objects.create(
        user_name=stored_params["person"],
        email=stored_params["email"],
        symptoms=symptoms_text,  
        date=stored_params["suggested_date"],
        time=stored_params["suggested_time"],
        doctor=doctor_obj
    )

    formatted_dt = datetime.strptime(f"{stored_params['suggested_date']} {stored_params['suggested_time']}", "%Y-%m-%d %H:%M:%S")
    formatted_time_text = formatted_dt.strftime("%A, %d %B %Y at %I:%M %p")

    return JsonResponse({
        "fulfillmentText": (
            f"Appointment confirmed for {stored_params['person']} on {formatted_time_text} "
            f"with Dr. {stored_params['doctor']} ({stored_params['specialization']}) for symptoms: {symptoms_text}."
        )
    })

    
def extract_context_params(output_contexts, context_name):
    for ctx in output_contexts:
        if context_name in ctx["name"]:
            return {
                "person": ctx["parameters"].get("person", ""),
                "email": ctx["parameters"].get("email", ""),
                "doctor": ctx["parameters"].get("doctor", ""),
                "specialization": ctx["parameters"].get("specialization", ""),
                "symptoms": ctx["parameters"].get("symptoms", ""),
                "user_symptoms": ctx["parameters"].get("user_symptoms", []),
                "user_symptoms_text": ctx["parameters"].get("user_symptoms_text", ""),
                "suggested_date": ctx["parameters"].get("suggested_date", ""),
                "suggested_time": ctx["parameters"].get("suggested_time", ""),
                "appointment_id": ctx["parameters"].get("appointment_id", ""),
                "new_date": ctx["parameters"].get("new_date", ""),
                "new_time": ctx["parameters"].get("new_time", ""),
            }
    return None



def cancel_appointment(output_contexts, parameters):
    """Handles appointment cancellation by ensuring a name is provided and retrieving appointments."""
    
    # Extract name 
    person = extract_person(parameters)

    # If not found, extracts from stored context
    if not person:
        stored_person = extract_context_params(output_contexts, "awaiting_cancellation_name").get("person", "")
        person = str(stored_person) if isinstance(stored_person, str) else ""

    # If the extracted name is a dictionary, extract "name" field
    if isinstance(person, dict) and "name" in person:
        person = str(person["name"]).strip()

    # If no name is provided, prompt again
    if not person:
        return JsonResponse({
            "fulfillmentText": "I need to know whose appointment to cancel. Can you tell me the name?",
            "outputContexts": [
                {
                    "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_cancellation_name",
                    "lifespanCount": 3
                }
            ]
        })

    # Debugging logs
    #print(f"Extracted name for cancellation: {person}")

    # Retrieve all appointments for this user
    appointments = Appointment.objects.filter(user_name=person)

    # Debugging logs
    #print(f"Appointments found for {person}: {list(appointments)}")

    # If no appointments exist, **remove context to stop looping**
    if not appointments.exists():
        return JsonResponse({
            "fulfillmentText": f"{person}, you don't have any scheduled appointments to cancel.",
            "outputContexts": [
                {
                    "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_cancellation_name",
                    "lifespanCount": 0  
                }
            ]
        })

    # If only one appointment exists, cancel it directly
    if appointments.count() == 1:
        appointment = appointments.first()
        appointment.delete()
        return JsonResponse({
            "fulfillmentText": f"{person}, your appointment with Dr. {appointment.doctor.name} on {appointment.date} at {appointment.time} has been canceled.",
            "outputContexts": [
                {
                    "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_cancellation_name",
                    "lifespanCount": 0  
                }
            ]
        })
    appointment_options = []
    for i, appt in enumerate(appointments):
        formatted_dt = datetime.strptime(f"{appt.date} {appt.time}", "%Y-%m-%d %H:%M:%S")
        readable_time = formatted_dt.strftime("%A, %d %B %Y at %I:%M %p")
        appointment_options.append(f"{i+1}. {readable_time} with Dr. {appt.doctor.name} ({appt.doctor.specialization})")

    # If multiple appointments exist, prompts the user to choose one
    appointment_list_text = "\n".join(appointment_options)

    return JsonResponse({
        "fulfillmentText": f"You have multiple appointments. Please select one or more to cancel:\n{appointment_list_text}",
        "outputContexts": [
            {
                "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_appointment_selection",
                "lifespanCount": 3,
                "parameters": {"person": person}
            },
            {
                "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_cancellation_name",
                "lifespanCount": 0 
            }
        ]
    })

def confirm_cancel_appointment(output_contexts, parameters):
    """Final step: Cancels multiple appointments selected by the user."""

    # Extract stored user information
    stored_params = extract_context_params(output_contexts, "awaiting_appointment_selection")
    person = stored_params.get("person", "")

    #Ensure person is correctly extracted from different possible structures
    if isinstance(person, dict):
        person = person.get("name", "")

    #Extract number selection (can be a single number or a list)
    selected_indexes = parameters.get("Number", []) or parameters.get("number", [])

    if not person:
        return JsonResponse({"fulfillmentText": "I need to know whose appointment to cancel. Can you tell me the name?"})

    if not selected_indexes:
        return JsonResponse({"fulfillmentText": "I didn't understand which appointments you want to cancel. Please try again."})

    # Convert to list if it's a single number
    if isinstance(selected_indexes, int):
        selected_indexes = [selected_indexes]

    # Retrieve all appointments again
    appointments = list(Appointment.objects.filter(user_name=person))
 
    if not appointments:
        return JsonResponse({"fulfillmentText": f"{person}, you don't have any scheduled appointments to cancel."})

    # Track successfully deleted appointments
    deleted_appointments = []

    for index in selected_indexes:
        try:
            selected_index = int(index) - 1 
            if selected_index < 0 or selected_index >= len(appointments):
                continue

            appointment_to_delete = appointments[selected_index]
            deleted_appointments.append(
                f"{appointment_to_delete.date} at {appointment_to_delete.time} with Dr. {appointment_to_delete.doctor.name} ({appointment_to_delete.doctor.specialization})"
            )
            appointment_to_delete.delete()

        except (ValueError, TypeError):
            continue  # Skip invalid selections

    if not deleted_appointments:
        return JsonResponse({"fulfillmentText": "Invalid selection. Please enter valid numbers."})

    # Generate appropriate response for singular or plural
    if len(deleted_appointments) == 1:
        response_text = f"{person}, your appointment on {deleted_appointments[0]} has been canceled."
    else:
        response_text = f"{person}, the following appointments have been canceled:\n" + "\n".join(deleted_appointments)

    return JsonResponse({"fulfillmentText": response_text})

def reschedule_appointment(output_contexts, parameters):
    """Handles appointment rescheduling by suggesting a new time."""
    
    person = extract_person(parameters)

    if not person:
        stored_person = extract_context_params(output_contexts, "awaiting_reschedule").get("person", "")
        person = stored_person if stored_person else ""

    if not person:
        return JsonResponse({
            "fulfillmentText": "I need to know whose appointment you want to reschedule. Can you tell me the name?",
            "outputContexts": [
                {"name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_reschedule", "lifespanCount": 3}
            ]
        })

    #print(f"Extracted name for rescheduling: {person}")

    appointments = Appointment.objects.filter(user_name=person)

    if not appointments.exists():
        return JsonResponse({
            "fulfillmentText": f"{person}, you don't have any scheduled appointments to reschedule."
        })

    if appointments.count() == 1:
        return suggest_new_time(person, appointments.first())

    appointment_options = []
    for i, appt in enumerate(appointments):
        formatted_dt = datetime.strptime(f"{appt.date} {appt.time}", "%Y-%m-%d %H:%M:%S")
        readable_time = formatted_dt.strftime("%A, %d %B %Y at %I:%M %p")
        appointment_options.append(f"{i+1}. {readable_time} with Dr. {appt.doctor.name} ({appt.doctor.specialization})")

    appointment_list_text = "\n".join(appointment_options)

    return JsonResponse({
        "fulfillmentText": f"You have multiple appointments. Please select one to reschedule:\n{appointment_list_text}",
        "outputContexts": [
            {"name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_reschedule_selection", 
             "lifespanCount": 3, 
             "parameters": {"person": person}}
        ]
    })

def suggest_new_time(person, appointment):
    """Finds the next available slot for rescheduling and asks for confirmation."""
    
    doctor = appointment.doctor
    new_date, new_time = find_next_available_slot(doctor)

    # If no available slots
    if not new_date:
        return JsonResponse({"fulfillmentText": f"Sorry, Dr. {doctor.name} is fully booked for the next 2 weeks."})
    
    current_dt = datetime.strptime(f"{appointment.date} {appointment.time}", "%Y-%m-%d %H:%M:%S")
    new_dt = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M:%S")

    formatted_current = current_dt.strftime("%A, %d %B %Y at %I:%M %p")
    formatted_new = new_dt.strftime("%A, %d %B %Y at %I:%M %p")

    return JsonResponse({
        "fulfillmentText": (
            f"Your current appointment is on {formatted_current}. "
            f"The next available slot for Dr. {doctor.name} is on {formatted_new}. "
            f"Shall I reschedule your appointment to this time?"
        ),

        "outputContexts": [
            {
                "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/awaiting_reschedule_confirmation",
                "lifespanCount": 3,
                "parameters": {
                    "person": person,
                    "appointment_id": appointment.id,
                    "new_date": new_date,
                    "new_time": new_time
                }
            }
        ]
    })

def confirm_reschedule_appointment(output_contexts, parameters):
    """Finalizes appointment rescheduling and updates the database."""

    # Extract stored parameters
    stored_params = extract_context_params(output_contexts, "awaiting_reschedule_confirmation")
    if not stored_params:
        return JsonResponse({"fulfillmentText": "I couldn't find the details needed to reschedule. Please try again."})

    person = stored_params.get("person", "")
    if isinstance(person, dict):
        person = person.get("name", "")
    person = str(person).strip()

    appointment_id = stored_params.get("appointment_id", "")
    new_date = stored_params.get("new_date", "")
    new_time = stored_params.get("new_time", "")

    # Ensure all necessary parameters exist
    if not (person and appointment_id and new_date and new_time):
        return JsonResponse({"fulfillmentText": "I couldn't process your rescheduling request. Please try again."})

    # Retrieve the appointment
    appointment = Appointment.objects.filter(id=appointment_id, user_name=person).first()

    if not appointment:
        return JsonResponse({"fulfillmentText": "I couldn't find the appointment to reschedule."})

    # Update appointment with new date and time
    appointment.date = new_date
    appointment.time = new_time
    appointment.save()

    # Convert to formatted datetime
    formatted_dt = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M:%S")
    formatted_time_text = formatted_dt.strftime("%A, %d %B %Y at %I:%M %p")

    return JsonResponse({
        "fulfillmentText": f"{person}, your appointment has been rescheduled to {formatted_time_text} with Dr. {appointment.doctor.name}."
    })


def confirm_reschedule_selection(output_contexts, parameters):
    """User selects the appointment they want to reschedule."""
    stored_params = extract_context_params(output_contexts, "awaiting_reschedule_selection")
    person = stored_params.get("person", "")

    if isinstance(person, dict):
        person = person.get("name", "")

    selection = parameters.get("number", [])
    if isinstance(selection, (int, float)):
        selection = [int(selection)]
    elif isinstance(selection, list):
        selection = [int(s) for s in selection if isinstance(s, (int, float))]

    if not person or not selection:
        return JsonResponse({"fulfillmentText": "I didn't get which appointment you want to reschedule. Please try again."})

    appointments = list(Appointment.objects.filter(user_name=person))

    if not appointments:
        return JsonResponse({"fulfillmentText": f"{person}, you don't have any scheduled appointments."})

    selected_index = selection[0] - 1

    if selected_index < 0 or selected_index >= len(appointments):
        return JsonResponse({"fulfillmentText": "Invalid selection. Please select a valid appointment number."})

    selected_appointment = appointments[selected_index]

    return suggest_new_time(person, selected_appointment)

def suggest_alternative_time(output_contexts):
    stored = (
        extract_context_params(output_contexts, "appointment_confirm")
        or extract_context_params(output_contexts, "awaiting_reschedule_confirmation")
    )
    if not stored:
        return JsonResponse({"fulfillmentText": "Sorry, I couldn't retrieve the previous appointment details to suggest a new time."})

    doctor_name = stored.get("doctor")
    person = stored.get("person")
    symptoms = stored.get("symptoms", "").split(", ")

    # Extract and normalize previous attempts (ensure it's list of tuples)
    previous_attempts = [tuple(x) for x in stored.get("previous_attempts", [])]

    prev_date = stored.get("suggested_date")
    prev_time = stored.get("suggested_time")

    if prev_date and prev_time and (prev_date, prev_time) not in previous_attempts:
        previous_attempts.append((prev_date, prev_time))

    doctor = None
    if doctor_name:
        doctor = Doctor.objects.filter(name=doctor_name).first()

    if not doctor and stored.get("appointment_id"):
        appointment = Appointment.objects.filter(id=stored["appointment_id"]).first()
        if appointment:
            doctor = appointment.doctor
            doctor_name = doctor.name
        else:
            return JsonResponse({"fulfillmentText": "Sorry, I couldn't retrieve the appointment to find the doctor."})

    if not doctor:
        return JsonResponse({"fulfillmentText": "Sorry, I couldn't find the doctor to suggest a new time."})

    # Try new slots while avoiding previous_attempts
    for _ in range(10):
        new_date, new_time = find_next_available_slot(doctor, excluded_slots=set(previous_attempts))
        if new_date and new_time and (new_date, new_time) not in previous_attempts:
            break
    else:
        return JsonResponse({"fulfillmentText": f"Sorry, Dr. {doctor_name} is fully booked."})

    # Add this newly suggested time to previous attempts
    previous_attempts.append((new_date, new_time))

    formatted_dt = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M:%S")
    formatted_time_text = formatted_dt.strftime("%A, %d %B %Y at %I:%M %p")

    return JsonResponse({
        "fulfillmentText": (
            f"Okay, how about {formatted_time_text} with Dr. {doctor_name}? Should I book it for {person}?"
        ),
        "outputContexts": [
            {
                "name": "projects/appointment-dcgw/agent/sessions/session_id/contexts/appointment_confirm",
                "lifespanCount": 5,
                "parameters": {
                    "person": person,
                    "doctor": doctor_name,
                    "specialization": stored.get("specialization"),
                    "symptoms": stored.get("symptoms"),
                    "suggested_date": new_date,
                    "suggested_time": new_time,
                    "previous_attempts": [list(x) for x in previous_attempts]
                }
            }
        ]
    })

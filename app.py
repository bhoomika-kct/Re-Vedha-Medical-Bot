from flask import Flask, render_template, request, jsonify
from utils import read_json, write_json, append_json, get_next_patient_id
import random
import logging
import json
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    session = request.json.get("session", {})
    
    logging.info(f"User input: {user_input}, Session: {session}")

    # Check for goodbye FIRST, before any other processing
    exit_words = ["bye", "exit", "thank you", "thanks", "goodbye"]
    if any(word in user_input.lower() for word in exit_words):
        return jsonify(
            response="Thank you for chatting with HealthBot! 💚 Stay healthy!",
            session={}  # Clear the session to end the conversation
        )

    # STEP 1: Start conversation
    if "step" not in session:
        session["step"] = "get_id"
        return jsonify(
            response="👋 Hi there! Are you an existing patient? Please enter your Patient ID.",
            session=session
        )

    # STEP 2: Check Patient ID
    if session["step"] == "get_id":
        if not user_input:
            return jsonify(
                response="⚠️ Please provide a valid Patient ID.",
                session=session
            )
        session["patient_id"] = user_input
        try:
            patients = read_json("patients.json")
            patient = next((p for p in patients if p["id"] == session["patient_id"]), None)
        except FileNotFoundError:
            logging.error("patients.json not found")
            return jsonify(
                response="⚠️ Sorry, our system is having trouble. Please try again later.",
                session=session
            )
        except json.JSONDecodeError:
            logging.error("patients.json is malformed")
            return jsonify(
                response="⚠️ Sorry, our system is having trouble. Please try again later.",
                session=session
            )
        except Exception as e:
            logging.error(f"Error reading patients.json: {str(e)}")
            return jsonify(
                response="⚠️ An error occurred. Please try again.",
                session=session
            )

        if patient:
            session["step"] = "get_symptoms"
            session["patient_name"] = patient["name"]
            return jsonify(
                response=(
                    f"Welcome back, {patient['name']}! 😊 \n"
                    "How are you feeling today? Please describe your symptoms."
                ),
                session=session
            )
        else:
            session["step"] = "get_new_user_info"
            return jsonify(
                response="❗ I couldn't find your ID. Are you a new patient? Please reply with your Name, Age, and Gender (comma separated).",
                session=session
            )

    # STEP 3: Register New Patient
    if session["step"] == "get_new_user_info":
        try:
            name, age, gender = map(str.strip, user_input.split(","))
            new_patient = {
                "id": get_next_patient_id(),
                "name": name,
                "age": int(age),
                "gender": gender,
                "linked_doctor_id": None
            }
            try:
                append_json("patients.json", new_patient)
            except Exception as e:
                logging.error(f"Error appending to patients.json: {str(e)}")
                return jsonify(
                    response="⚠️ Sorry, we couldn't register you. Please try again.",
                    session=session
                )
            session["step"] = "get_symptoms"
            session["patient_name"] = name
            return jsonify(
                response=f"Nice to meet you, {name}! 😊 Now tell me what symptoms you're experiencing.",
                session=session
            )
        except ValueError:
            return jsonify(
                response="⚠️ Please provide your details correctly like: John Doe, 28, Male",
                session=session
            )

    # STEP 4: Get Symptoms
    if session["step"] == "get_symptoms":
        if not user_input or len(user_input.strip()) < 3 or user_input.isdigit():
            return jsonify(
                response="🤔 Could you please describe your symptoms in more detail?",
                session=session
            )
        session["symptoms"] = user_input
        severity = calculate_severity(user_input)
        session["severity_score"] = severity

        if severity >= 3:  # Lowered threshold
            session["step"] = "show_doctor"
            return jsonify(
                response=f"😟 I'm concerned about your symptoms (Score: {severity}/10).<br>Let's get you to a doctor right away.",
                session=session
            )
        else:
            suggestion = get_basic_suggestion(user_input)
            return jsonify(
                response = f"🩺 Your symptoms seem mild (Score: {severity}/10).<br><strong>Here's some advice:</strong> {suggestion}. Anything else you're feeling?",
                session=session
            )

    # STEP 5: Recommend Doctor
    if session["step"] == "show_doctor":
        try:
            doctors = read_json("doctors.json")
            patients = read_json("patients.json")
            patient = next((p for p in patients if p["id"] == session["patient_id"]), None)
        except FileNotFoundError:
            logging.error("doctors.json or patients.json not found")
            return jsonify(
                response="⚠️ Sorry, our system is having trouble. Please try again later.",
                session=session
            )
        except json.JSONDecodeError:
            logging.error("doctors.json or patients.json is malformed")
            return jsonify(
                response="⚠️ Sorry, our system is having trouble. Please try again later.",
                session=session
            )
        except Exception as e:
            logging.error(f"Error reading JSON files: {str(e)}")
            return jsonify(
                response="⚠️ An error occurred. Please try again.",
                session=session
            )

        if not doctors:
            logging.error("No doctors available in doctors.json")
            session["step"] = "get_symptoms"  # Fallback to symptoms
            return jsonify(
                response=(
                    "⚠️ Sorry, no doctors are available right now. "
                    "Please describe any additional symptoms you’re experiencing, and I’ll do my best to help."
                ),
                session=session
            )

        doctor = None
        if patient and patient["linked_doctor_id"]:
            doctor = next((d for d in doctors if d["id"] == patient["linked_doctor_id"]), None)
        if not doctor:
            doctor = random.choice(doctors)
            if patient:
                patient["linked_doctor_id"] = doctor["id"]
                try:
                    write_json("patients.json", patients)
                except Exception as e:
                    logging.error(f"Error writing to patients.json: {str(e)}")
                    return jsonify(
                        response="⚠️ Sorry, we couldn't assign a doctor. Please try again.",
                        session=session
                    )

        session["doctor_id"] = doctor["id"]
        session["doctor_name"] = doctor["name"]
        session["step"] = "book_appointment"

        available_12hr = [format_time(h) for h in doctor['available_timings']]

        return jsonify(
            response=(
                f"👨‍⚕️ I recommend Dr. {doctor['name']} ({doctor['specialty']}).\n"
                f"Available slots: {' - '.join(available_12hr)}.\n"
                "When would you like to book the appointment?"
            ),
            session=session
        )

    # STEP 6: Book Appointment
    if session["step"] == "book_appointment":
        try:
            doctors = read_json("doctors.json")
            doctor = next((d for d in doctors if d["id"] == session["doctor_id"]), None)

            if not doctor:
                logging.error(f"Doctor ID {session['doctor_id']} not found")
                session["step"] = "get_symptoms"  # Fallback
                return jsonify(
                    response="⚠️ Sorry, we couldn’t find that doctor. Please describe any additional symptoms.",
                    session=session
                )

            user_time_str = extract_time_in_24hr(user_input)
            if not user_time_str:
                return jsonify(
                    response="⚠️ Sorry, I couldn't understand the time you mentioned. Please try again like 'book at 10am' or 'at 2:30pm'.",
                    session=session
                )

            # Extract hour for availability comparison
            user_hour = int(user_time_str.split(":")[0])
            start_time = int(doctor["available_timings"][0])
            end_time = int(doctor["available_timings"][1])

            available_12hr = [format_time(h) for h in doctor['available_timings']]

            if not (start_time <= user_hour <= end_time):
                return jsonify(
                    response=f"⚠️ Sorry, that time isn’t available. Please choose between {' - '.join(available_12hr)}",
                    session=session
                )

            # All good - Save the appointment
            appointment = {
                "patient_id": session["patient_id"],
                "doctor_id": session["doctor_id"],
                "appointment_time": user_time_str  # Save clean 24hr format
            }

            try:
                append_json("appointments.json", appointment)
            except Exception as e:
                logging.error(f"Error appending to appointments.json: {str(e)}")
                return jsonify(
                    response="⚠️ Sorry, we couldn't book the appointment. Please try again.",
                    session=session
                )

            session["step"] = "get_symptoms"
            return jsonify(
                response=f"✅ Appointment confirmed with Dr. {session['doctor_name']} at {user_time_str}. Anything else you're feeling, {session['patient_name']}?",
                session=session
            )

        except Exception as e:
            logging.error(f"Unexpected error in book_appointment: {str(e)}")
            return jsonify(
                response="⚠️ Oops, something went wrong while booking. Let's try again from the symptoms.",
                session=session
            )

        except FileNotFoundError:
            logging.error("doctors.json not found")
            return jsonify(
                response="⚠️ Sorry, our system is having trouble. Please try again later.",
                session=session
            )
        except json.JSONDecodeError:
            logging.error("doctors.json is malformed")
            return jsonify(
                response="⚠️ Sorry, our system is having trouble. Please try again later.",
                session=session
            )
        except Exception as e:
            logging.error(f"Error in booking appointment: {str(e)}")
            return jsonify(
                response="⚠️ An error occurred. Please try again.",
                session=session
            )

    # FINAL fallback
    response = "🤖 Sorry, I didn't understand that."
    if session["step"] == "get_symptoms":
        response += " Could you please describe your symptoms again?"
    elif session["step"] == "book_appointment":
        response += " Please choose a valid appointment time."
    else:
        response += " Could you please clarify or say 'bye' to end the chat?"
    return jsonify(
        response=response,
        session=session
    )

def format_time(hour_str):
    hour = int(hour_str)
    suffix = "AM" if hour < 12 or hour == 24 else "PM"
    hour_12 = hour % 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    return f"{hour_12} {suffix}"

def extract_time_in_24hr(user_input):
    # Step 1: Extract time pattern using regex
    match = re.search(r'(\d{1,2})([:.](\d{2}))?\s*(am|pm)', user_input.lower())
    if not match:
        return None  # No time found

    hour = int(match.group(1))
    minute = int(match.group(3)) if match.group(3) else 0
    am_pm = match.group(4)

    # Step 2: Convert to 24hr time
    time_obj = datetime.strptime(f"{hour}:{minute:02d} {am_pm}", "%I:%M %p")
    return time_obj.strftime("%H:%M")  # returns string like '08:30'


def calculate_severity(symptoms_text):
    high_risk_keywords = {
        "chest pain": 7,  # Higher weight for critical symptoms
        "shortness of breath": 7,
        "fever": 3,
        "dizziness": 3
    }
    score = 0
    symptoms_text = symptoms_text.lower()
    for keyword, weight in high_risk_keywords.items():
        if keyword in symptoms_text:
            score += weight
    return min(score, 10)

def get_basic_suggestion(symptoms_text):
    if "headache" in symptoms_text.lower():
        return "Drink water and rest. Avoid screen time."
    if "cold" in symptoms_text.lower():
        return "Try steam inhalation and stay warm."
    return "Monitor your condition and take rest."

if __name__ == "__main__":
    app.run(debug=True)
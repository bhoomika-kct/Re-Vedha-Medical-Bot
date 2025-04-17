import json
import os

# Path constants
BASE_PATH = 'data'
FILES = {
    'patients': 'patients.json',
    'doctors': 'doctors.json',
    'reports': 'reports.json',
    'appointments': 'appointments.json',
    'feedback': 'feedback.json'
}

# Load and save helpers
def load_data(file_key):
    path = os.path.join(BASE_PATH, FILES[file_key])
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return json.load(f)

def save_data(file_key, data):
    path = os.path.join(BASE_PATH, FILES[file_key])
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

# Patient-related
def get_patient_by_id(patient_id):
    patients = load_data('patients')
    return next((p for p in patients if p['id'] == patient_id), None)

def add_new_patient(name, age, symptoms, doctor_id):
    patients = load_data('patients')
    existing_ids = [p['id'] for p in patients if 'id' in p]
    next_id = max(existing_ids, default=0) + 1

    new_patient = {
        "id": next_id,
        "name": name,
        "age": age,
        "symptoms": symptoms,
        "doctor_id": doctor_id
    }

    patients.append(new_patient)
    save_data('patients', patients)
    return next_id

def get_next_patient_id():
    patients = load_data('patients')
    ids = [p['id'] for p in patients if 'id' in p and isinstance(p['id'], str) and p['id'].startswith('P')]

    numeric_ids = []
    for pid in ids:
        try:
            numeric_ids.append(int(pid[1:]))  # Remove 'P' and convert
        except ValueError:
            continue  # Skip junk like "no" or corrupted IDs

    next_id_num = max(numeric_ids, default=0) + 1
    return f'P{next_id_num:03d}'

# Doctor-related
def get_all_doctors():
    return load_data('doctors')

def find_suitable_doctor(symptom):
    doctors = load_data('doctors')
    symptom = symptom.lower()
    # Dumb mapping for now — better version later
    for doc in doctors:
        if symptom in doc['specialty'].lower():
            return doc
    return doctors[0]  # fallback to first doctor

def get_doctor_by_id(doc_id):
    doctors = load_data('doctors')
    return next((d for d in doctors if d['id'] == doc_id), None)

# Appointment-related
def get_available_timings(doctor_id):
    doc = get_doctor_by_id(doctor_id)
    return doc['available_timings'] if doc else []

def book_appointment(patient_id, doctor_id, date, time):
    appointments = load_data('appointments')
    appointments.append({
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": date,
        "time": time
    })
    save_data('appointments', appointments)

# Reports
def get_patient_report(patient_id):
    reports = load_data('reports')
    return next((r['report'] for r in reports if r['patient_id'] == patient_id), None)

# Feedback
def save_feedback(patient_id, feedback):
    feedbacks = load_data('feedback')
    feedbacks.append({
        "patient_id": patient_id,
        "feedback": feedback
    })
    save_data('feedback', feedbacks)

# Severity Score Logic
def calculate_severity(symptoms):
    severity_keywords = {
        "chest pain": 5,
        "shortness of breath": 5,
        "fever": 3,
        "headache": 2,
        "sore throat": 2,
        "fatigue": 1
    }
    score = sum(severity_keywords.get(sym.lower(), 1) for sym in symptoms)
    return score

def read_json(filename):
    filename = os.path.join(BASE_PATH, filename)
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def write_json(filename, data):
    filename = os.path.join(BASE_PATH, filename)
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def append_json(filename, new_entry):
    data = read_json(filename)
    data.append(new_entry)
    write_json(filename, data)

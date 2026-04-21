import os
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
from datetime import datetime




load_dotenv()
# Use the secure URI from your .env file
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri, tlsCAFile=certifi.where())

# This is the global 'db' variable main.py is looking for
db = client.lakshya_institute

def get_db():
    uri = os.getenv("MONGODB_URI")
    client = MongoClient(uri, tlsCAFile=certifi.where())
    return client.lakshya_institute

def generate_admission_id():
    db = get_db()
    year = datetime.now().strftime("%y") 
    student_count = db.students.count_documents({})
    return f"LAK-{year}-{student_count + 1:03d}"

def add_student(name, class_name, parent_phone, monthly_fee, join_date):
    db = get_db()
    admission_id = generate_admission_id()
    join_dt = datetime.combine(join_date, datetime.min.time())
    
    student = {
        "admission_id": admission_id,
        "name": name.strip().title(),
        "class_name": str(class_name).strip(),
        "parent_phone": parent_phone.strip(),
        "monthly_fee": float(monthly_fee),
        "joining_date": join_dt,
        "total_paid": 0.0, 
        "status": "Active"
    }
    db.students.insert_one(student)
    return admission_id

def fetch_all_students():
    return list(get_db().students.find())

def log_payment(admission_id, amount_paid, payment_mode="Cash"):
    db = get_db()
    now = datetime.now()
    amount = float(amount_paid)
    
    transaction = {
        "admission_id": admission_id,
        "amount": amount,
        "date": now,
        "mode": payment_mode,
        "receipt_number": f"REC-{int(now.timestamp())}"
    }
    db.transactions.insert_one(transaction)
    
    db.students.update_one(
        {"admission_id": admission_id},
        {"$inc": {"total_paid": amount}}
    )

def fetch_student_transactions(admission_id):
    return list(get_db().transactions.find({"admission_id": admission_id}).sort("date", -1))

def fetch_all_transactions():
    return list(get_db().transactions.find())

# --- UPDATED: Now handles both status and fee ---
def update_student_record(admission_id, new_status, new_fee):
    db = get_db()
    db.students.update_one(
        {"admission_id": admission_id},
        {"$set": {
            "status": new_status,
            "monthly_fee": float(new_fee)
        }}
    )

def delete_student(admission_id):
    db = get_db()
    db.students.delete_one({"admission_id": admission_id})
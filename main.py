from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import os
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client.lakshya_db  

# --- DATA MODELS ---
class StudentModel(BaseModel):
    name: str
    mobile_no: str  
    student_class: str
    fees: int
    institute_id: str

class TransactionModel(BaseModel):
    student_id: str
    student_name: str
    student_class: str
    institute_id: str
    amount: int
    month_paid_for: str

class StatusUpdateModel(BaseModel):
    status: str

# --- AUTOMATIC BILLING PROCESSOR (FEATURE #10) ---
def process_billing_cycles(institute_id: str):
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    # Find all active students whose billing date has arrived or passed
    due_students = db.students.find({
        "institute_id": institute_id,
        "status": "active",
        "next_billing_date": {"$lte": today_str}
    })
    
    for student in due_students:
        # Add the monthly fee to their current due amount
        new_due = student.get("due_amount", 0) + student.get("fees", 0)
        
        # Move their next billing date forward by 30 days
        current_billing = datetime.strptime(student["next_billing_date"], "%Y-%m-%d")
        next_billing = (current_billing + timedelta(days=30)).strftime("%Y-%m-%d")
        
        db.students.update_one(
            {"_id": student["_id"]},
            {"$set": {
                "due_amount": new_due,
                "is_paid": False,
                "next_billing_date": next_billing
            }}
        )

# --- ENDPOINTS ---
@app.get("/api/dashboard-stats")
async def get_dashboard_stats(institute_id: str = "LAKSHYA_001"):
    # Run the billing processor so data is perfectly accurate
    process_billing_cycles(institute_id)
    
    now = datetime.now()
    current_month_name = now.strftime("%B")
    trial_limit = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    
    total_students = db.students.count_documents({"institute_id": institute_id, "status": "active"})
    
    first_day = now.replace(day=1).strftime("%Y-%m-%d")
    new_regs = db.students.count_documents({"institute_id": institute_id, "joining_date": {"$gte": first_day}})

    # Collected Revenue
    tx_pipeline = [
        {"$match": {"institute_id": institute_id, "month_paid_for": current_month_name}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    tx_result = list(db.transactions.aggregate(tx_pipeline))
    collected = tx_result[0]["total"] if tx_result else 0

    # Pending Revenue (Excluding Trials)
    due_pipeline = [
        {"$match": {
            "institute_id": institute_id, 
            "status": "active", 
            "joining_date": {"$lt": trial_limit} 
        }},
        {"$group": {"_id": None, "total": {"$sum": "$due_amount"}}}
    ]
    due_result = list(db.students.aggregate(due_pipeline))
    pending = due_result[0]["total"] if due_result else 0

    return {
        "total_students": total_students,
        "new_registrations": new_regs,
        "collected_revenue": collected,
        "pending_revenue": pending,
        "expected_total": collected + pending,
        "month_name": current_month_name
    }

@app.post("/api/students")
async def add_student(student: StudentModel):
    now = datetime.now()
    student_dict = student.dict()
    student_dict["joining_date"] = now.strftime("%Y-%m-%d")
    student_dict["status"] = "active"
    student_dict["is_paid"] = False 
    student_dict["due_amount"] = student.fees 
    
    # Set the exact date the next payment will automatically be added
    student_dict["next_billing_date"] = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    
    db.students.insert_one(student_dict)
    return {"message": "Student Registered Successfully"}

@app.get("/api/students")
async def get_students(institute_id: str = "LAKSHYA_001"):
    process_billing_cycles(institute_id) # Update dues before showing list
    students = list(db.students.find({"institute_id": institute_id}))
    for s in students:
        s["_id"] = str(s["_id"])
    return students

@app.post("/api/transactions")
async def record_transaction(tx: TransactionModel):
    now = datetime.now()
    tx_dict = tx.dict()
    tx_dict["date"] = now.strftime("%Y-%m-%d")
    tx_dict["time"] = now.strftime("%H:%M")
    db.transactions.insert_one(tx_dict)
    
    student = db.students.find_one({"_id": ObjectId(tx.student_id)})
    if student:
        new_due = student.get("due_amount", student["fees"]) - tx.amount
        db.students.update_one(
            {"_id": ObjectId(tx.student_id)},
            {"$set": {"due_amount": max(0, new_due), "is_paid": new_due <= 0}}
        )
    return {"message": "Payment Recorded"}

@app.patch("/api/students/{student_id}/status")
async def update_status(student_id: str, data: StatusUpdateModel):
    db.students.update_one({"_id": ObjectId(student_id)}, {"$set": {"status": data.status}})
    return {"message": "Status updated"}

@app.delete("/api/students/{student_id}")
async def delete_student(student_id: str):
    db.students.delete_one({"_id": ObjectId(student_id)})
    return {"message": "Student deleted"}

@app.get("/api/transactions")
async def get_transactions(institute_id: str = "LAKSHYA_001", name: str = "", student_class: str = ""):
    query = {"institute_id": institute_id}
    if name: query["student_name"] = {"$regex": name, "$options": "i"}
    if student_class: query["student_class"] = {"$regex": student_class, "$options": "i"}
    transactions = list(db.transactions.find(query).sort("date", -1))
    for t in transactions: t["_id"] = str(t["_id"])
    return transactions
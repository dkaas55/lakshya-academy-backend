from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import os
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for mobile app access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client.lakshya_db  

# --- DATA MODELS ---
class StudentModel(BaseModel):
    name: str
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

# --- ENDPOINTS ---

@app.get("/api/dashboard-stats")
async def get_dashboard_stats(institute_id: str = "LAKSHYA_001"):
    # 1. Total Active Students
    total_students = db.students.count_documents({"institute_id": institute_id, "status": "active"})
    
    # 2. New Registrations (Current Month)
    first_day_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d")
    new_regs = db.students.count_documents({
        "institute_id": institute_id,
        "joining_date": {"$gte": first_day_of_month}
    })
    
    # 3. Expected Revenue (Sum of fees of all active students)
    pipeline = [
        {"$match": {"institute_id": institute_id, "status": "active"}},
        {"$group": {"_id": None, "total": {"$sum": "$fees"}}}
    ]
    revenue_result = list(db.students.aggregate(pipeline))
    expected_revenue = revenue_result[0]["total"] if revenue_result else 0

    return {
        "total_students": total_students,
        "new_registrations": new_regs,
        "expected_revenue": expected_revenue
    }

@app.post("/api/students")
async def add_student(student: StudentModel):
    now = datetime.now()
    student_dict = student.dict()
    student_dict["joining_date"] = now.strftime("%Y-%m-%d")
    student_dict["status"] = "active"
    student_dict["is_paid"] = False # Trial period starts
    
    # Set permanent billing day based on registration date
    student_dict["billing_day"] = now.day 
    
    db.students.insert_one(student_dict)
    return {"message": "Student Registered Successfully"}

@app.get("/api/students")
async def get_students(institute_id: str = "LAKSHYA_001"):
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
    
    # 1. Save to transactions collection
    db.transactions.insert_one(tx_dict)
    
    # 2. Update student status to paid
    db.students.update_one(
        {"_id": ObjectId(tx.student_id)},
        {"$set": {"is_paid": True}}
    )
    return {"message": "Payment Recorded Successfully"}

@app.get("/api/transactions")
async def get_transactions(institute_id: str = "LAKSHYA_001", name: str = "", student_class: str = ""):
    query = {"institute_id": institute_id}
    if name:
        query["student_name"] = {"$regex": name, "$options": "i"}
    if student_class:
        query["student_class"] = {"$regex": student_class, "$options": "i"}
        
    transactions = list(db.transactions.find(query).sort("date", -1))
    for t in transactions:
        t["_id"] = str(t["_id"])
    return transactions
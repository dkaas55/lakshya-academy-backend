from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
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
class StatusUpdateModel(BaseModel):
    status: str
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

# --- ENDPOINTS ---

@app.get("/api/dashboard-stats")
async def get_dashboard_stats(institute_id: str = "LAKSHYA_001"):
    total_students = db.students.count_documents({"institute_id": institute_id, "status": "active"})
    
    first_day_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d")
    new_regs = db.students.count_documents({
        "institute_id": institute_id,
        "joining_date": {"$gte": first_day_of_month}
    })
    
    # Collected Money (Sum of transactions this month)
    current_month = datetime.now().strftime("%B")
    tx_pipeline = [
        {"$match": {"institute_id": institute_id, "month_paid_for": current_month}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    tx_result = list(db.transactions.aggregate(tx_pipeline))
    collected_money = tx_result[0]["total"] if tx_result else 0

    # Total Due Amount (Sum of pending dues for active students)
    due_pipeline = [
        {"$match": {"institute_id": institute_id, "status": "active"}},
        {"$group": {"_id": None, "total": {"$sum": "$due_amount"}}}
    ]
    due_result = list(db.students.aggregate(due_pipeline))
    total_due = due_result[0]["total"] if due_result else 0

    return {
        "total_students": total_students,
        "new_registrations": new_regs,
        "collected_money": collected_money,
        "total_due": total_due
    }

@app.post("/api/students")
async def add_student(student: StudentModel):
    now = datetime.now()
    student_dict = student.dict()
    student_dict["joining_date"] = now.strftime("%Y-%m-%d")
    student_dict["status"] = "active"
    student_dict["is_paid"] = False 
    student_dict["billing_day"] = now.day 
    
    # Initialize the due amount to the full fee upon registration
    student_dict["due_amount"] = student.fees
    
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
    
    db.transactions.insert_one(tx_dict)
    
    # Find student to update their due amount mathematically
    student = db.students.find_one({"_id": ObjectId(tx.student_id)})
    if student:
        current_due = student.get("due_amount", student.get("fees", 0))
        new_due = current_due - tx.amount
        is_paid = new_due <= 0  # Only true if they paid everything
        
        db.students.update_one(
            {"_id": ObjectId(tx.student_id)},
            {"$set": {
                "due_amount": max(0, new_due), 
                "is_paid": is_paid
            }}
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
@app.patch("/api/students/{student_id}/status")
async def toggle_student_status(student_id: str, status_data: StatusUpdateModel):
    db.students.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"status": status_data.status}}
    )
    return {"message": f"Student status changed to {status_data.status}"}

@app.delete("/api/students/{student_id}")
async def delete_student(student_id: str):
    # This completely removes the student from the database
    db.students.delete_one({"_id": ObjectId(student_id)})
    return {"message": "Student permanently deleted"}
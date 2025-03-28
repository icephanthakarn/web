# add_user.py

from app import app  # นำเข้า app จากไฟล์หลักของคุณ
from models import db, UserModel
from werkzeug.security import generate_password_hash

# ข้อมูลตัวอย่างนักศึกษา
sample_students = [
    {
        "student_id": "64050166",
        "student_name": "พันธกานต์ กิจนุกร",
        "student_major": "วิศวกรรมคอมพิวเตอร์",
        "student_year": "graduate",
        "email": "64050166@kmitl.ac.th",
        "password": "50166"  # จะถูก hash ก่อนเก็บ
    },

        {
        "student_id": "64050466",
        "student_name": "ดุสิตา บุญหนุน",
        "student_major": "วิศวกรรมคอมพิวเตอร์",
        "student_year": "graduate",
        "email": "64050456@kmitl.ac.th",
        "password": "50456"  # จะถูก hash ก่อนเก็บ
    },

        {
        "student_name": "Admin",
        "email": "admin@kmitl.ac.th",
        "role": "admin",
        "password": "1234"
    },

]


with app.app_context():
    for student in sample_students:
        existing_user = UserModel.query.filter_by(email=student["email"]).first()

        if existing_user:
            print(f"⚠️ ผู้ใช้ {student['email']} มีอยู่แล้วในระบบ")
        else:
            hashed_password = generate_password_hash(student["password"])
            new_user = UserModel(
                student_id=student.get("student_id"),
                student_name=student.get("student_name"),
                student_major=student.get("student_major"),
                student_year=student.get("student_year"),
                email=student["email"],
                password=hashed_password,
                role=student.get("role", "student")  # ถ้าไม่มี role ให้ใช้ student เป็น default
            )
            db.session.add(new_user)
            print(f"✅ เพิ่มผู้ใช้ใหม่: {student['email']}")

    db.session.commit()
    print("🎉 เสร็จสิ้นการเพิ่มข้อมูลผู้ใช้ลงในฐานข้อมูล")

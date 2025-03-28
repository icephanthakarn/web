from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from werkzeug.utils import secure_filename
import os
from models import db, ProjectModel, UserModel, PdfFileModel, ProjectStudentModel, KeywordModel, ProjectKeywordModel, ProjectAdvisorModel
from ocr_logic import process_pdf_to_data
from werkzeug.security import check_password_hash, generate_password_hash  # <- ถ้าต้องการใช้ generate_password_hash
from flask_migrate import Migrate
import random
from pdf2image import convert_from_path


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# === Settings ===
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydb.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()

# === Index page ===
@app.route('/')
def index():
    projects = ProjectModel.query.all()
    return render_template('index.html', projects=projects)

# === Login ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = UserModel.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user'] = {'id': user.id, 'name': user.student_name}
            
            # เช็ค role
            if user.role == 'admin':
                # ถ้าเป็น admin ให้เด้งไปหน้า /admin
                return redirect(url_for('admin_page'))
            else:
                # ถ้าไม่ใช่ admin ให้ไปหน้า index หรือ profile ตามสะดวก
                return redirect(url_for('index'))
        else:
            flash('อีเมลหรือรหัสผ่านไม่ถูกต้อง')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# === Upload PDF + OCR ===
@app.route('/upload', methods=['GET', 'POST'])
def upload_project():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        uploaded_file = request.files['pdf_file']
        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(save_path)
            session['uploaded_filename'] = filename
            session['uploaded_file_path'] = save_path
            ocr_data = process_pdf_to_data(save_path)
            return render_template('upload.html', uploaded_filename=filename, ocr_data=ocr_data)

    return redirect(url_for('profile'))

# === Submit project info and save to DB ===
@app.route('/submit-info', methods=['POST'])
def fill_project_info():
    file_path = session.get('uploaded_file_path')
    user_info = session.get('user')
    user = UserModel.query.get(user_info['id']) if user_info else None

    pdf_filename = session['uploaded_filename']  # เช่น "mydoc.pdf"
    pdf_full_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    # 1) สร้าง ProjectModel
    project = ProjectModel(
        title_th=request.form['title'],
        title_en=request.form['alt_title'],
        author=request.form['author'],
        abstract_th=request.form['abstract'],
        faculty=request.form['faculty'],
        department=request.form['department'],
        academic_year=request.form.get('academic_year', ''),
        advisor=request.form['advisor'],
        keywords=request.form['keywords'],
        file_path=os.path.join('static', 'uploads', pdf_filename)
    )
    db.session.add(project)
    db.session.commit()

    # 2) แปลงหน้าแรก PDF → รูป thumbnail
    # ถ้าบน Windows ต้องระบุ poppler_path=... ถ้าใช้ Linux/macOS อาจไม่ต้อง
    pages = convert_from_path(pdf_full_path, 200)  # DPI=200
    if pages:
        # ตั้งชื่อรูป thumbnail จากชื่อ PDF เช่น mydoc_thumb.jpg
        thumb_filename = pdf_filename.rsplit('.', 1)[0] + "_thumb.jpg"
        thumb_full_path = os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename)

        # บันทึกหน้าแรกเป็นไฟล์ .jpg
        pages[0].save(thumb_full_path, 'JPEG')

        # (3) ได้ไฟล์รูปแล้ว -> สร้าง path สำหรับเก็บใน DB 
        thumbnail_path = os.path.join('static', 'uploads', thumb_filename)
        thumbnail_path = thumbnail_path.replace('\\', '/')  # กันปัญหา backslash บน Windows

        # อัปเดตฟิลด์ project.thumbnail_path
        project.thumbnail_path = thumbnail_path
        db.session.commit()

    db.session.commit()

    # 3) ความสัมพันธ์ ProjectStudent, PdfFileModel, Keyword (เดิม)
    if user:
        db.session.add(ProjectStudentModel(project_id=project.id, user_id=user.id, role='ผู้จัดทำหลัก'))

    db.session.add(PdfFileModel(file_name=pdf_filename, file_path=project.file_path, project_id=project.id))

    keyword_list = [kw.strip() for kw in request.form['keywords'].split(',') if kw.strip()]
    for kw in keyword_list:
        keyword_obj = KeywordModel.query.filter_by(keyword_text=kw).first()
        if not keyword_obj:
            keyword_obj = KeywordModel(keyword_text=kw)
            db.session.add(keyword_obj)
            db.session.flush()
        db.session.add(ProjectKeywordModel(project_id=project.id, keyword_id=keyword_obj.id))

    advisor_user = UserModel.query.filter_by(student_name=project.advisor, role='advisor').first()
    if advisor_user:
        db.session.add(ProjectAdvisorModel(project_id=project.id, advisor_id=advisor_user.id, role='ที่ปรึกษาหลัก'))

    db.session.commit()

    # ล้าง session upload
    session['user_project'] = {
        'title': project.title_th,
        'alt_title': project.title_en,
        'year': project.academic_year,
        'faculty': project.faculty,
        'department': project.department
    }
    session.pop('uploaded_file_path', None)
    session.pop('uploaded_filename', None)

    return redirect(url_for('profile'))

# === Profile Page ===
@app.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    project = ProjectModel.query.filter_by(author=user['name']).first()

    return render_template('profile.html',
                           user_name=user['name'],
                           student_id=user['id'],
                           faculty="วิทยาศาสตร์",
                           department="วิทยาการคอมพิวเตอร์",
                           user_project=session.get('user_project'),
                           project=project)

# === Project Detail ===
@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = ProjectModel.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/delete-project', methods=['POST'])
def delete_project():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))

    user_in_db = UserModel.query.get(user['id'])

    # ลบเฉพาะโปรเจกต์ที่เป็นของ user หรือถ้า user เป็น admin
    project = ProjectModel.query.filter_by(author=user['name']).first()

    # สมมติเราอนุญาตให้ admin ลบได้หมด
    if user_in_db.role == 'admin':
        # ดึงโปรเจกต์จาก request.form หรือดูเองว่าจะใช้แบบไหน
        project_id = request.form.get('project_id', None)
        if project_id:
            project = ProjectModel.query.get(project_id)
    else:
        # ถ้าไม่ใช่ admin ใช้เงื่อนไขเดิม
        project = ProjectModel.query.filter_by(author=user['name']).first()

    if project:
        # ลบ record
        db.session.delete(project)
        db.session.commit()

    session.pop('user_project', None)
    return redirect(url_for('profile'))



@app.route('/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    project = ProjectModel.query.get_or_404(project_id)

    if request.method == 'POST':
        project.title_th = request.form['title']
        project.title_en = request.form['alt_title']
        project.author = request.form['author']
        project.abstract_th = request.form['abstract']
        project.faculty = request.form['faculty']
        project.department = request.form['department']
        project.academic_year = request.form['academic_year']
        project.advisor = request.form['advisor']
        project.keywords = request.form['keywords']
        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('edit_project.html', project=project)

def is_admin():
    user_session = session.get('user')
    if not user_session:
        return False
    user_in_db = UserModel.query.get(user_session['id'])
    if user_in_db and user_in_db.role == 'admin':
        return True
    return False




@app.route('/admin', methods=['GET'])
def admin_page():
    # ตรวจสอบสิทธิ์
    if not is_admin():
        flash("คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        return redirect(url_for('index'))
    
    all_projects = ProjectModel.query.all()
    return render_template('admin.html', projects=all_projects)


# ส่วน Admin: ลบโปรเจกต์ใด ๆ ก็ตาม
@app.route('/admin/delete-project/<int:project_id>', methods=['POST'])
def admin_delete_project(project_id):
    if not is_admin():
        flash("คุณไม่มีสิทธิ์เข้าถึงฟังก์ชันนี้")
        return redirect(url_for('index'))
    
    project = ProjectModel.query.get_or_404(project_id)
    # ลบไฟล์จริงในโฟลเดอร์ (ถ้าต้องการ)
    if project.file_path:
        file_full_path = os.path.join(app.root_path, project.file_path)
        if os.path.exists(file_full_path):
            os.remove(file_full_path)
    # ลบข้อมูลใน DB
    db.session.delete(project)
    db.session.commit()
    flash(f"ลบโปรเจกต์ #{project_id} เรียบร้อยแล้ว")
    return redirect(url_for('admin_page'))


@app.route('/create_admin')
def create_admin():
    admin_user = UserModel(
        email="admin@example.com",
        password=generate_password_hash("admin123"),
        role="admin",
        student_name="System Administrator"
    )
    db.session.add(admin_user)
    db.session.commit()
    return "Admin created!"


# === Context Processor ===
@app.context_processor
def inject_user():
    user = session.get('user')
    if user:
        user_in_db = UserModel.query.get(user['id'])
        first_letter = user['name'][0].upper() if user['name'] else "U"
        colors = ['#ea5c0d', '#e67e22', '#16a085', '#2980b9', '#8e44ad']
        avatar_color = colors[hash(user['id']) % len(colors)]

        # เพิ่มฟิลด์บอกใน template ว่าปัจจุบันเป็น admin ไหม
        user_is_admin = (user_in_db.role == 'admin') if user_in_db else False

        return dict(
            user_logged_in=True,
            student_id=user['id'],
            first_letter=first_letter,
            avatar_color=avatar_color,
            user_is_admin=user_is_admin
        )
    return dict(user_logged_in=False)

if __name__ == '__main__':
    app.run(debug=True)
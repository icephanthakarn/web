from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime

db = SQLAlchemy()

class UserModel(db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='student')  # <-- Role มีค่า student, admin, advisor, ฯลฯ

    student_id = Column(String(10))
    student_name = Column(String(100))
    student_major = Column(String(100))
    student_year = Column(String(10))

    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.datetime.now)

    projects = relationship('ProjectModel', secondary='project_student', back_populates='students')
    advising_projects = relationship('ProjectModel', secondary='project_advisor', back_populates='advisors')

    @classmethod
    def authenticate(cls, email, password):
        user = cls.query.filter_by(email=email).first()
        if user and user.password == password:
            return user
        return None


class ProjectModel(db.Model):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title_th = Column(String(255), nullable=False)
    title_en = Column(String(255))
    academic_year = Column(String(10))
    abstract_th = Column(Text)
    abstract_en = Column(Text)
    department = Column(String(100))
    faculty = Column(String(100))

    author = Column(String(255))
    advisor = Column(String(255))
    keywords = Column(String(255))
    file_path = Column(String(255))
    thumbnail_path = Column(String(255))   # <--- เพิ่มบรรทัดนี้

    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.datetime.now)

    students = relationship('UserModel', secondary='project_student', back_populates='projects')
    keywords_rel = relationship('KeywordModel', secondary='project_keyword', back_populates='projects')
    advisors = relationship('UserModel', secondary='project_advisor', back_populates='advising_projects')
    pdf_files = relationship('PdfFileModel', back_populates='project')


class ProjectStudentModel(db.Model):
    __tablename__ = 'project_student'

    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role = Column(String(50))


class ProjectAdvisorModel(db.Model):
    __tablename__ = 'project_advisor'

    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    advisor_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role = Column(String(50))


class KeywordModel(db.Model):
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword_text = Column(String(100), nullable=False)

    projects = relationship('ProjectModel', secondary='project_keyword', back_populates='keywords_rel')


class ProjectKeywordModel(db.Model):
    __tablename__ = 'project_keyword'

    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    keyword_id = Column(Integer, ForeignKey('keywords.id'), primary_key=True)


class PdfFileModel(db.Model):
    __tablename__ = 'pdf_file'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.now)

    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship('ProjectModel', back_populates='pdf_files')


@property
def keywords_list(self):
    return self.keywords_rel

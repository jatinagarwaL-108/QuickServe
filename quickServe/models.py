from datetime import datetime

from flask_login import UserMixin
from sqlalchemy.sql import func

from .extensions import db, login_manager

BOOKING_STATUSES = ('Pending', 'Accepted', 'Rejected', 'Completed', 'Cancelled')



class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    services = db.relationship('Service', backref='category', lazy=True)


class Area(db.Model):
    __table_args__ = (db.UniqueConstraint('city', 'name', name='uq_area_city_name'),)

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    users = db.relationship('User', backref='area', lazy=True)
    services = db.relationship('Service', backref='area', lazy=True)



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='customer')  # customer/provider/admin
    location = db.Column(db.String(100))        # old free-text field, kept for now
    phone = db.Column(db.String(20))
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=True)   # NEW


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)   # old free-text field, kept for now
    is_available = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)   # NEW
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=True)           # NEW

    provider = db.relationship('User', backref='services')

    @property
    def avg_rating(self):
        avg = db.session.query(func.avg(Review.rating)).filter(
            Review.service_id == self.id
        ).scalar()
        return round(float(avg), 1) if avg else 0


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    customer_name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    address = db.Column(db.String(200))
    date = db.Column(db.String(50))     # old string fields, kept for now
    time = db.Column(db.String(50))
    payment_method = db.Column(db.String(20))
    rating = db.Column(db.Integer, default=0)   # old rating, Review replaces it
    status = db.Column(db.String(20), default="Pending")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    problem_description = db.Column(db.Text, nullable=True)
    resolution_status = db.Column(db.String(30),default='Unknown',nullable=False)

    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    outcome_verified = db.Column(db.Boolean,default=False,nullable=False)

    # NEW columns (the agent will use these later; adding them now saves a migration)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    idempotency_key = db.Column(db.String(64), unique=True, nullable=True)
    created_by = db.Column(db.String(20), default='user')   # 'user' or 'agent'

    service = db.relationship('Service', backref='bookings', lazy=True)
    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_bookings', lazy=True)
    provider = db.relationship('User', foreign_keys=[provider_id], backref='provider_bookings', lazy=True)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    complaint_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Pending")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="complaints")


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    sender_role = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)



class Review(db.Model):
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='ck_review_rating'),
    )

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False, unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)    # 1 to 5
    text = db.Column(db.Text)                         # review words, used for search in Stage 3+
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    booking = db.relationship('Booking', backref=db.backref('review', uselist=False))
    customer = db.relationship('User', foreign_keys=[customer_id], backref='reviews_written')
    provider = db.relationship('User', foreign_keys=[provider_id], backref='reviews_received')
    service = db.relationship('Service', backref='reviews')


class chatbotSession(db.Model):
    __tablename__ = "chatbot_session"

    id = db.Column(db.Integer,primary_key = True)
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    status = db.Column(db.String(30),default = "Collection",nullable = False)
    collected_data = db.Column(db.JSON,default=dict,nullable=False)

    created_at = db.Column(db.DateTime,default=datetime.utcnow)

    updated_at = db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

    messages = db.relationship("ChatbotMessage",backref="session",cascade="all, delete-orphan",lazy=True)

class ChatbotMessage(db.Model):
    __tablename__ = "chatbot_message"

    id = db.Column(db.Integer,primary_key=True)

    session_id = db.Column(db.Integer,db.ForeignKey("chatbot_session.id"),nullable = False)
    sender = db.Column(db.String(20),nullable=False)
    message = db.Column(db.Text,nullable = False)
    created_at = db.Column(db.DateTime,default=datetime.utcnow)

    
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
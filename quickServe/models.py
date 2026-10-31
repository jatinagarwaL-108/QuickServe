from datetime import datetime

from flask_login import UserMixin
from sqlalchemy.sql import func

from .extensions import db,login_manager


class User(UserMixin,db.Model):

    id = db.Coloum(db.Integer, primary_key = True)
    username = db.Column(db.string(150),nullable=False , unique = True)
    email = db.Column(db.string(150),nullable=False , unique = True)
    password = db.Column(db.string(150),nullable=False)
    role = db.Column(db.string(50),nullable=False , default = 'customer')
    location = db.Column(db.string(100))
    phone = db.Column(db.string(20))


class Service(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    provider_id = db.Column(db.Integer,db.foreignKey('user.id'),nullable = False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    provider = db.relationship('User', backref = 'services')

    @property
    def avg_rating(self):
        avg = db.session.query(func.avg(Booking.rating)).filter(
            Booking.service_id == self.id,
            Booking.rating > 0
        ).scalar()
        return round(avg,1) if avg else 0



class Booking(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    customer_id = db.Column(db.Integer,db.foreignKey('user.id'),nullable = False)
    provider_id = db.Column(db.Integer,db.foreignKey('user.id'),nullable = False)
    service_id = db.Column(db.Integer,db.foreignKey('user.id'),nullable = False)
    customer_name = db.Column(db.string(150))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    address = db.Column(db.String(200))
    date = db.Column(db.String(50))
    time = db.Column(db.String(50))
    payment_method = db.Column(db.String(20))
    rating = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="Pending")
    timestamp = db.Column(db.DateTime, default=datetime.timezone.utc)

    service = db.relationship('Service',backref = 'bookings',lazy = True)
    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_bookings', lazy=True)
    provider = db.relationship('User', foreign_keys=[provider_id], backref='provider_bookings', lazy=True)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer,db.foreignKey('user_id'),nullable = False)
    complaint_text = db.Column(db.Text,nullable = False)
    status = db.Column(db.String(50),default = "Pending")
    timestamp = db.Column(db.DateTime, default = datetime.timezone.utc)

    user = db.relationship("User",backref = "complaints")

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    sender_role = db.Column(db.String(20))  # 'customer' or 'provider'
    timestamp = db.Column(db.DateTime, default=datetime.timezone.utc)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User,int(user_id))


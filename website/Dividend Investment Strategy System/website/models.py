from . import db 
from flask_login import UserMixin
from sqlalchemy.sql import func

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data  = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())

class CompanyInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    companyname = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(255))
    value_diff = db.Column(db.String(255))
    perc_diff = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    company_info = db.relationship('CompanyInfo', backref='user', lazy='dynamic')

class Stocks(db.Model):
    stock_code = db.Column(db.String(50), primary_key=True)
    stock_name = db.Column(db.String(255))
    historical_prices = db.relationship('Historical', backref='stock', lazy=True)
    
class Historical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Date = db.Column(db.String(255))
    Open = db.Column(db.Float)
    High = db.Column(db.Float)
    Low = db.Column(db.Float)
    Close = db.Column(db.Float)
    stock_code = db.Column(db.String(255), db.ForeignKey('stocks.stock_code'))



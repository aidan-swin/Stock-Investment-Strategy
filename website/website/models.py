from . import db 
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime

class CompanyInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    companyname=db.Column(db.String(150))
    equity_ratio = db.Column(db.Float)
    equity_ratio_i = db.Column(db.Float)
    liabilities_coverage = db.Column(db.Float)
    liabilities_coverage_i = db.Column(db.Float)
    operating_profit_margin_to_financial_expense = db.Column(db.Float)
    operating_profit_margin_to_financial_expense_i = db.Column(db.Float)
    working_capital_to_fixed_assets = db.Column(db.Float)
    working_capital_to_fixed_assets_i = db.Column(db.Float)
    current_liabilities_by_365_by_cost_of_products_sold = db.Column(db.Float)
    current_liabilities_by_365_by_cost_of_products_sold_i = db.Column(db.Float)
    operating_expenses_to_total_liabilities = db.Column(db.Float)
    operating_expenses_to_total_liabilities_i = db.Column(db.Float)
    current_assets_without_inventories_to_liabilities = db.Column(db.Float)
    current_assets_without_inventories_to_liabilities_i = db.Column(db.Float)
    liability_to_operating_profit_ratio_per_day = db.Column(db.Float)
    liability_to_operating_profit_ratio_per_day_i = db.Column(db.Float)
    net_profit_to_inventory = db.Column(db.Float)
    net_profit_to_inventory_i = db.Column(db.Float)
    assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation= db.Column(db.Float)
    assets_without_inventories_and_short_term_liabilities_to_sales_without_gross_profit_and_depreciation_i = db.Column(db.Float)
    forecast_period= db.Column(db.Float)
    date = db.Column(db.Date(), default=datetime.today().date())
    Bankrupt = db.Column(db.Float)
    Risk=db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    admin_user = db.Column(db.Boolean, default=False)
    subscribed = db.Column(db.Boolean, default=False)
    userwatchlist = db.relationship('Watchlist', backref='user', lazy=True)
    userportfolio = db.relationship('Portfolio', backref='user', lazy=True)

class Stocks(db.Model):
    stock_code = db.Column(db.String(50), primary_key=True)
    stock_name = db.Column(db.String(255))
    address1 = db.Column(db.String(255))
    address2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    zip = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    website = db.Column(db.String(255))
    industry = db.Column(db.String(100))
    sector = db.Column(db.String(100))
    fullTimeEmployees = db.Column(db.Integer)
    stockratios = db.relationship('Ratiottm', backref='stock', lazy=True)
    stockwatchlists = db.relationship('Watchlist', backref='stock', lazy=True)
    stockdividends = db.relationship('Dividend', backref='stock', lazy=True)
    stockquarterreport = db.relationship('Quarter', backref='stock', lazy=True)
    stockportfolio = db.relationship('Portfolio', backref='stock', lazy=True)

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(255), db.ForeignKey('stocks.stock_code'), nullable=False)
    user_id = db.Column(db.String(255), db.ForeignKey('user.id'), nullable=False)

class Ratiottm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(255), db.ForeignKey('stocks.stock_code'), nullable=False)
    rDY = db.Column(db.Float)
    rPR = db.Column(db.Float)
    rOM = db.Column(db.Float)
    rFCF = db.Column(db.Float)
    rPE = db.Column(db.Float)
    rROE = db.Column(db.Float)
    rEPS = db.Column(db.Float)
    rDPS = db.Column(db.Float)
    rClass = db.Column(db.String(1))
    rDate = db.Column(db.Date(), default=datetime.today().date()) # Use db.Date for date columns

class Dividend(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stock_code = db.Column(db.String(255), db.ForeignKey('stocks.stock_code'), nullable=False)
    dAnnceDate = db.Column(db.Date())
    dExDate = db.Column(db.Date())
    dPayDate = db.Column(db.Date())
    dAmount = db.Column(db.Float)

class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Date = db.Column(db.Date)
    Open = db.Column(db.Float)
    High = db.Column(db.Float)
    Low = db.Column(db.Float)
    Close = db.Column(db.Float)
    Volume = db.Column(db.Float)
    stock_code = db.Column(db.String(255), db.ForeignKey('stocks.stock_code'))

class Quarter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    revenue = db.Column(db.Float)
    capitalExpenditures = db.Column(db.Float)
    grossDividend = db.Column(db.Float)
    netIncome = db.Column(db.Float)
    operatingCashFlow = db.Column(db.Float)
    operatingIncome = db.Column(db.Float)
    preferredDividends = db.Column(db.Float)
    sharesOutstanding = db.Column(db.Float)
    totalEquity = db.Column(db.Float)
    stock_code = db.Column(db.String(50), db.ForeignKey('stocks.stock_code'))

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(50), db.ForeignKey('stocks.stock_code'))
    user_id = db.Column(db.String(255), db.ForeignKey('user.id'), nullable=False)
    unitQuantity = db.Column(db.Integer)
    purchaseDate = db.Column(db.Date)

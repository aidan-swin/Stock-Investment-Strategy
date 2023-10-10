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
    company_info = db.relationship('CompanyInfo', backref='user', lazy='dynamic')

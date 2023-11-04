from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

db = SQLAlchemy()
DB_NAME = "database.db"
DB_INITIALIZED_FLAG = "db_initialized"


def create_app():
    #initialize app. this is what runs when the program begins
    app = Flask (__name__)
    app.config['SECRET_KEY'] = 'remilia scarlet'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)
        
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Ratiottm, Stocks, Watchlist, Price, Dividend, Quarter
    
    # Check if the database has already been initialized
    if not app.config.get(DB_INITIALIZED_FLAG):
        create_database(app)
        app.config[DB_INITIALIZED_FLAG] = True

    admin = Admin(app, name='My App', template_mode='bootstrap3')
    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(Ratiottm, db.session))
    admin.add_view(ModelView(Stocks, db.session))
    admin.add_view(ModelView(Watchlist,db.session))
    admin.add_view(ModelView(Price,db.session))
    admin.add_view(ModelView(Dividend,db.session))
    admin.add_view(ModelView(Quarter,db.session))

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def create_database(app):
    if not path.exists('instance/' + DB_NAME):
        with app.app_context():
            csv_file_path = "csvdata/stocks_with_information.csv"  # Replace with the path to your CSV file
            df = pd.read_csv(csv_file_path)
            df.to_sql('Stocks', con=db.engine, if_exists='replace', index=False)

            csv_file_path = "csvdata/historicalprices.csv"  # Replace with the path to your CSV file
            df = pd.read_csv(csv_file_path, low_memory=False)
            df = df.reset_index().rename(columns={'index': 'id'})
            df.to_sql('Price', con=db.engine, if_exists='replace', index=False)

            csv_file_path = "csvdata/historicaldividends_cleaned.csv"  # Replace with the path to your CSV file
            df = pd.read_csv(csv_file_path)
            df = df.reset_index().rename(columns={'index': 'id'})
            df.to_sql('Dividend', con=db.engine, if_exists='replace', index=False)

            csv_file_path = "csvdata/stock_financial_quarterly.csv"
            df = pd.read_csv(csv_file_path)
            df = df.reset_index().rename(columns={'index': 'id'})
            df.to_sql('Quarter', con=db.engine, if_exists='replace', index=False)

            csv_file_path = "csvdata/stock_ratio_quarterly.csv"
            df = pd.read_csv(csv_file_path)
            df = df.reset_index().rename(columns={'index': 'id'})
            df.to_sql('Ratiottm', con=db.engine, if_exists='replace', index=False)

            db.create_all()
            print('Created Database!')
            from .models import User
            
            # Check if the admin user already exists
            admin_user = User.query.filter_by(email='admin@ambank.com').first()
            if not admin_user:
                # If the admin user does not exist, create a new user
                new_user = User(email="admin@ambank.com", first_name="Admin", password=generate_password_hash("testing", method='sha256'), admin_user = True)
                db.session.add(new_user)
                db.session.commit()
                print('Created Admin User!')
            else:
                # If the admin user already exists, skip creating a new user
                print('Admin User Already Exists!')

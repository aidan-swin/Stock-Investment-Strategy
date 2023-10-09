from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import pandas as pd

db = SQLAlchemy()
DB_NAME = "database.db"

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

    from .models import User, CompanyInfo, Stocks, Historical, Ratio

    create_database(app)

    admin = Admin(app, name='My App', template_mode='bootstrap3')
    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(CompanyInfo, db.session))
    admin.add_view(ModelView(Stocks, db.session))
    admin.add_view(ModelView(Historical, db.session))
    admin.add_view(ModelView(Ratio, db.session))

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def create_database(app):
    # Check if the database file exists
    if not path.exists('website/' + DB_NAME):

        # After creating the database, create the tables for your models
        from .models import User, CompanyInfo
        with app.app_context():
            
            csv_file_path = "csvdata/stocks.csv"  # Replace with the path to your CSV file
            df = pd.read_csv(csv_file_path)
            df.to_sql('Stocks', con=db.engine, if_exists='replace', index=False)

            csv_file_path = "csvdata/stock_class_rounded.csv"
            df = pd.read_csv(csv_file_path)
            df = df.reset_index().rename(columns={'index': 'id'})
            df.to_sql('Ratio', con=db.engine, if_exists='replace', index=False)
            db.create_all()
           

        print('Created Database!')

            
        
        

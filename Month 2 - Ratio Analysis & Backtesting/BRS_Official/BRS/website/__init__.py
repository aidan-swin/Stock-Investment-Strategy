from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash

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

    from .models import User, CompanyInfo
    
    create_database(app)

    admin = Admin(app, name='My App', template_mode='bootstrap3')
    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(CompanyInfo, db.session))

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def create_database(app):
    if not path.exists('website/' + DB_NAME):
        with app.app_context():
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

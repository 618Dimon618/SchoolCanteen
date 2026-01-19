from app import app
from models_db import db

with app.app_context():
    db.create_all()
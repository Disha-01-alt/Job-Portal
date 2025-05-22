from flask_login import UserMixin
from database import get_user_by_id

def setup_auth(login_manager):
    @login_manager.user_loader
    def load_user(user_id):
        return get_user_by_id(int(user_id))

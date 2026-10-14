# Calendar Module for Sofia System
# Universal Calendar Generator with Traditional Chinese Features

from flask import Blueprint

calendar_bp = Blueprint('calendar', __name__, 
                       template_folder='templates',
                       static_folder='static',
                       url_prefix='/calendar')

from .routes import *
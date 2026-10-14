"""
Sofia System Integration Configuration
Calendar Module Registration and Setup
"""

from flask import Flask
from calendar_module import calendar_bp

def register_calendar_blueprint(app: Flask):
    """
    Register the calendar module as a blueprint in Sofia system
    
    Args:
        app: Flask application instance
    """
    
    # Register the calendar blueprint
    app.register_blueprint(calendar_bp)
    
    # Add calendar-specific configurations
    app.config.setdefault('CALENDAR_FEATURES', {
        'enable_pdf_export': True,
        'enable_lunar_calendar': True,
        'enable_auspicious_days': True,
        'max_export_years': 10,
        'default_year_range': (1900, 2100)
    })
    
    print("✅ Calendar module registered successfully")
    
    return app

def setup_calendar_database(db):
    """
    Setup database tables for calendar module (if needed)
    
    Args:
        db: SQLAlchemy database instance
    """
    
    # Calendar module can work without database
    # But we can add user preferences, custom events, etc.
    
    pass

# Calendar module metadata
CALENDAR_MODULE_INFO = {
    'name': 'Universal Calendar Generator',
    'version': '1.0.0',
    'description': '通用年历生成器 - 支持农历、节气、黄道吉日等传统文化元素',
    'author': 'Sofia System',
    'url_prefix': '/calendar',
    'features': [
        '任意年份年历生成 (1900-2100)',
        '农历日期显示',
        '传统节日标注',
        '二十四节气显示',
        '黄道吉日计算',
        '多格式导出 (HTML/PDF/TXT)',
        '响应式设计'
    ],
    'dependencies': [
        'flask',
        'datetime',
        'calendar'
    ],
    'optional_dependencies': [
        'reportlab (PDF导出功能)',
        'zhdate (精确农历转换)'
    ]
}

# Menu configuration for Sofia system
CALENDAR_MENU_CONFIG = {
    'title': '📅 年历生成',
    'icon': 'fas fa-calendar-alt',
    'url': '/calendar/',
    'description': '生成精美年历，包含传统文化元素',
    'category': '工具',
    'order': 100
}
"""
Calendar Module Database Models
Personal holidays and custom events management
"""

from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extensions import db

class PersonalHoliday(db.Model):
    """个性化节日模型"""
    __tablename__ = 'personal_holidays'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)  # 可选：关联用户ID
    session_id = db.Column(db.String(255), nullable=True)  # 用于匿名用户
    
    # 节日信息
    name = db.Column(db.String(100), nullable=False, comment='节日名称')
    description = db.Column(db.Text, nullable=True, comment='节日描述')
    
    # 日期信息
    month = db.Column(db.Integer, nullable=False, comment='月份 (1-12)')
    day = db.Column(db.Integer, nullable=False, comment='日期 (1-31)')
    year = db.Column(db.Integer, nullable=True, comment='特定年份，为空则每年重复')
    
    # 节日类型和属性
    category = db.Column(db.String(50), default='personal', comment='节日类别')
    color = db.Column(db.String(7), default='#ff6b6b', comment='显示颜色')
    icon = db.Column(db.String(50), default='🎉', comment='节日图标')
    is_birthday = db.Column(db.Boolean, default=False, comment='是否为生日')
    is_recurring = db.Column(db.Boolean, default=True, comment='是否每年重复')
    
    # 提醒设置
    remind_days_before = db.Column(db.Integer, default=0, comment='提前几天提醒')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PersonalHoliday {self.name} ({self.month:02d}-{self.day:02d})>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'month': self.month,
            'day': self.day,
            'year': self.year,
            'category': self.category,
            'color': self.color,
            'icon': self.icon,
            'is_birthday': self.is_birthday,
            'is_recurring': self.is_recurring,
            'remind_days_before': self.remind_days_before,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'date_key': f"{self.month:02d}-{self.day:02d}"
        }
    
    @classmethod
    def get_user_holidays(cls, user_id=None, session_id=None, year=None):
        """获取用户的个性化节日"""
        query = cls.query.filter(cls.is_active == True)
        
        if user_id:
            query = query.filter(cls.user_id == user_id)
        elif session_id:
            query = query.filter(cls.session_id == session_id)
        
        # 如果指定年份，包含该年份的特定节日和重复节日
        if year:
            query = query.filter(
                (cls.year == year) | 
                (cls.year.is_(None) & cls.is_recurring == True)
            )
        
        return query.all()
    
    @classmethod
    def get_holidays_by_date(cls, month, day, user_id=None, session_id=None, year=None):
        """获取特定日期的个性化节日"""
        query = cls.query.filter(
            cls.month == month,
            cls.day == day,
            cls.is_active == True
        )
        
        if user_id:
            query = query.filter(cls.user_id == user_id)
        elif session_id:
            query = query.filter(cls.session_id == session_id)
        
        if year:
            query = query.filter(
                (cls.year == year) | 
                (cls.year.is_(None) & cls.is_recurring == True)
            )
        
        return query.all()

class HolidayTemplate(db.Model):
    """节日模板"""
    __tablename__ = 'holiday_templates'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(50), default='🎉')
    color = db.Column(db.String(7), default='#ff6b6b')
    description = db.Column(db.Text, nullable=True)
    is_birthday_template = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<HolidayTemplate {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'icon': self.icon,
            'color': self.color,
            'description': self.description,
            'is_birthday_template': self.is_birthday_template
        }

def init_holiday_templates(db):
    """初始化节日模板数据"""
    templates = [
        # 生日类
        {'name': '生日', 'category': 'birthday', 'icon': '🎂', 'color': '#ff69b4', 'is_birthday_template': True},
        {'name': '结婚纪念日', 'category': 'anniversary', 'icon': '💕', 'color': '#ff1493'},
        {'name': '恋爱纪念日', 'category': 'anniversary', 'icon': '💖', 'color': '#ff69b4'},
        
        # 工作类
        {'name': '入职纪念日', 'category': 'work', 'icon': '💼', 'color': '#4169e1'},
        {'name': '升职纪念日', 'category': 'work', 'icon': '📈', 'color': '#32cd32'},
        {'name': '项目截止日', 'category': 'work', 'icon': '⏰', 'color': '#ff4500'},
        
        # 家庭类
        {'name': '家庭聚会', 'category': 'family', 'icon': '👨‍👩‍👧‍👦', 'color': '#ffa500'},
        {'name': '孩子入学', 'category': 'family', 'icon': '🎒', 'color': '#20b2aa'},
        {'name': '搬家纪念日', 'category': 'family', 'icon': '🏠', 'color': '#8b4513'},
        
        # 健康类
        {'name': '体检日', 'category': 'health', 'icon': '🏥', 'color': '#dc143c'},
        {'name': '疫苗接种', 'category': 'health', 'icon': '💉', 'color': '#228b22'},
        
        # 学习类
        {'name': '考试日期', 'category': 'education', 'icon': '📝', 'color': '#4682b4'},
        {'name': '毕业纪念日', 'category': 'education', 'icon': '🎓', 'color': '#daa520'},
        
        # 其他
        {'name': '旅行出发', 'category': 'travel', 'icon': '✈️', 'color': '#00ced1'},
        {'name': '重要会议', 'category': 'meeting', 'icon': '🤝', 'color': '#696969'},
        {'name': '纪念日', 'category': 'memorial', 'icon': '🕯️', 'color': '#2f4f4f'}
    ]
    
    for template_data in templates:
        if not HolidayTemplate.query.filter_by(name=template_data['name']).first():
            template = HolidayTemplate(**template_data)
            db.session.add(template)
    
    try:
        db.session.commit()
        print("✅ Holiday templates initialized successfully")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error initializing holiday templates: {e}")
"""
Calendar Module Backend Routes
Sofia System Blueprint - Universal Calendar Generator

Features:
- Generate calendars for any year (1900-2100)
- Traditional Chinese calendar elements
- Lunar dates, festivals, solar terms
- Auspicious days with traditional calculations
- Personal holidays and custom events
- Multiple export formats (HTML, PDF, TXT)
"""

from flask import Blueprint, render_template, request, jsonify, send_file, session
from datetime import datetime, date
import calendar as cal
import json
import tempfile
import os
from io import BytesIO
import base64
import uuid

from . import calendar_bp
from .calendar_engine import CalendarGenerator
from .models import PersonalHoliday, HolidayTemplate, init_holiday_templates
from extensions import db

@calendar_bp.route('/help/auspicious')
def help_auspicious():
    """Auspicious day calculation help page"""
    return render_template('help_auspicious.html')

@calendar_bp.route('/')
def index():
    """Calendar module main page"""
    current_year = datetime.now().year
    return render_template('calendar_index.html', current_year=current_year)

@calendar_bp.route('/api/generate', methods=['POST'])
def generate_calendar():
    """API endpoint to generate calendar data"""
    try:
        data = request.get_json()
        
        year = int(data.get('year', datetime.now().year))
        options = data.get('options', {})
        
        # Validate year range
        if not (1900 <= year <= 2100):
            return jsonify({'error': '年份必须在1900-2100之间'}), 400
        
        # Get or create session ID for personal holidays
        session_id = request.headers.get('X-Session-ID', str(uuid.uuid4()))
        
        # Initialize calendar generator
        generator = CalendarGenerator()
        
        # Generate calendar data with session_id for personal holidays
        calendar_data = generator.generate_calendar_data(year, options, session_id)
        
        return jsonify({
            'success': True,
            'year': year,
            'data': calendar_data,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/export/<format_type>', methods=['POST'])
def export_calendar(format_type):
    """Export calendar in specified format"""
    try:
        data = request.get_json()
        year = int(data.get('year', datetime.now().year))
        options = data.get('options', {})
        
        # 获取session_id以包含个性化节日
        session_id = get_user_session_id()
        
        generator = CalendarGenerator()
        
        if format_type == 'html':
            content = generator.generate_html(year, options, session_id)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                           delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            return send_file(temp_path, 
                           as_attachment=True, 
                           download_name=f'{year}年历.html',
                           mimetype='text/html')
        
        elif format_type == 'pdf':
            try:
                pdf_content = generator.generate_pdf(year, options, session_id)
                
                # Check if PDF was generated successfully
                if len(pdf_content) < 1000:  # Less than 1KB suggests a problem
                    print(f"Warning: PDF file seems too small ({len(pdf_content)} bytes), offering HTML alternative")
                    # Generate HTML with print-friendly styling instead
                    html_content = generator.generate_html(year, options, session_id)
                    
                    # Add print-specific CSS
                    print_css = """
                    <style media="print">
                        body { background: white !important; }
                        .calendar-container { 
                            box-shadow: none !important; 
                            border-radius: 0 !important;
                            padding: 10px !important;
                        }
                        .months-grid { 
                            grid-template-columns: repeat(3, 1fr) !important;
                            gap: 10px !important;
                        }
                        @page { margin: 1cm; }
                    </style>
                    """
                    
                    # Insert print CSS before </head>
                    html_content = html_content.replace('</head>', print_css + '</head>')
                    
                    # Create temporary HTML file with PDF-friendly name
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                                   delete=False, encoding='utf-8') as f:
                        f.write(html_content)
                        temp_path = f.name
                    
                    # Return HTML file but suggest PDF printing
                    response = send_file(temp_path, 
                                       as_attachment=True, 
                                       download_name=f'{year}年历_可打印版.html',
                                       mimetype='text/html')
                    response.headers['X-PDF-Alternative'] = 'true'
                    return response
                
                return send_file(BytesIO(pdf_content),
                               as_attachment=True,
                               download_name=f'{year}年历.pdf',
                               mimetype='application/pdf')
                               
            except Exception as pdf_error:
                print(f"PDF generation failed: {pdf_error}")
                # Fall back to HTML with print styling
                html_content = generator.generate_html(year, options, session_id)
                
                # Add print-specific CSS for PDF conversion
                print_css = """
                <style media="print">
                    body { 
                        background: white !important; 
                        font-size: 12px !important;
                    }
                    .calendar-container { 
                        box-shadow: none !important; 
                        border-radius: 0 !important;
                        padding: 10px !important;
                        margin: 0 !important;
                    }
                    .months-grid { 
                        grid-template-columns: repeat(3, 1fr) !important;
                        gap: 8px !important;
                    }
                    .calendar-month {
                        page-break-inside: avoid;
                        margin-bottom: 10px;
                    }
                    @page { 
                        margin: 1cm; 
                        size: A4 landscape;
                    }
                </style>
                <script>
                    window.onload = function() {
                        alert('PDF生成遇到兼容性问题。\\n\\n建议操作：\\n1. 打开此HTML文件\\n2. 按Ctrl+P打印\\n3. 选择"保存为PDF"');
                    }
                </script>
                """
                
                html_content = html_content.replace('</head>', print_css + '</head>')
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                               delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_path = f.name
                
                return send_file(temp_path, 
                               as_attachment=True, 
                               download_name=f'{year}年历_请打印为PDF.html',
                               mimetype='text/html')
        
        elif format_type == 'txt':
            txt_content = generator.generate_txt(year, options, session_id)
            
            return send_file(BytesIO(txt_content.encode('utf-8')),
                           as_attachment=True,
                           download_name=f'{year}年历.txt',
                           mimetype='text/plain')
        
        else:
            return jsonify({'error': '不支持的导出格式'}), 400
            
    except Exception as e:
        print(f"Export error: {e}")
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/preview', methods=['POST'])
def preview_calendar():
    """Generate calendar preview HTML"""
    try:
        data = request.get_json()
        year = int(data.get('year', datetime.now().year))
        options = data.get('options', {})
        
        # Get or create session ID for personal holidays
        session_id = get_user_session_id()
        
        generator = CalendarGenerator()
        html_content = generator.generate_html(year, options, session_id)
        
        # Return HTML content directly as string (Flask will handle UTF-8 encoding)
        return jsonify({
            'success': True,
            'html_content': html_content
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/auspicious/<int:year>/<int:month>/<int:day>')
def get_auspicious_info(year, month, day):
    """Get auspicious day information for specific date"""
    try:
        generator = CalendarGenerator()
        auspicious_info = generator.get_auspicious_info(year, month, day)
        
        return jsonify({
            'success': True,
            'date': f'{year}-{month:02d}-{day:02d}',
            'auspicious': auspicious_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/lunar/<int:year>/<int:month>/<int:day>')
def get_lunar_info(year, month, day):
    """Get lunar calendar information for specific date"""
    try:
        generator = CalendarGenerator()
        lunar_info = generator.get_lunar_info(year, month, day)
        
        return jsonify({
            'success': True,
            'date': f'{year}-{month:02d}-{day:02d}',
            'lunar': lunar_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/festivals/<int:year>')
def get_festivals(year):
    """Get all festivals and special dates for a year"""
    try:
        generator = CalendarGenerator()
        festivals_data = generator.get_year_festivals(year)
        
        return jsonify({
            'success': True,
            'year': year,
            'festivals': festivals_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================================
# Personal Holidays API Routes
# ================================

def get_user_session_id():
    """获取用户会话ID"""
    # 优先使用请求头中的session_id（前端传递）
    header_session_id = request.headers.get('X-Session-ID')
    
    if header_session_id:
        return header_session_id
    
    # 否则使用Flask session管理
    if 'calendar_session_id' not in session:
        session['calendar_session_id'] = str(uuid.uuid4())
    
    return session['calendar_session_id']

@calendar_bp.route('/api/personal-holidays', methods=['GET'])
def get_personal_holidays():
    """获取个性化节日列表"""
    try:
        year = request.args.get('year', type=int)
        session_id = get_user_session_id()
        
        holidays = PersonalHoliday.get_user_holidays(
            session_id=session_id, 
            year=year
        )
        
        return jsonify({
            'success': True,
            'holidays': [holiday.to_dict() for holiday in holidays]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/personal-holidays', methods=['POST'])
def add_personal_holiday():
    """添加个性化节日"""
    try:
        data = request.get_json()
        session_id = get_user_session_id()
        
        # 验证必需字段
        if not all(k in data for k in ['name', 'month', 'day']):
            return jsonify({'error': '缺少必需字段：name, month, day'}), 400
        
        # 验证日期有效性
        month = int(data['month'])
        day = int(data['day'])
        
        if not (1 <= month <= 12):
            return jsonify({'error': '月份必须在1-12之间'}), 400
        
        if not (1 <= day <= 31):
            return jsonify({'error': '日期必须在1-31之间'}), 400
        
        # 检查日期是否在该月份有效
        try:
            import calendar as cal
            if day > cal.monthrange(2024, month)[1]:  # 使用2024年作为参考
                return jsonify({'error': f'{month}月没有{day}日'}), 400
        except:
            pass
        
        # 创建新的个性化节日
        holiday = PersonalHoliday(
            session_id=session_id,
            name=data['name'],
            description=data.get('description', ''),
            month=month,
            day=day,
            year=data.get('year'),  # 可选：特定年份
            category=data.get('category', 'personal'),
            color=data.get('color', '#ff6b6b'),
            icon=data.get('icon', '🎉'),
            is_birthday=data.get('is_birthday', False),
            is_recurring=data.get('is_recurring', True),
            remind_days_before=data.get('remind_days_before', 0)
        )
        
        db.session.add(holiday)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '个性化节日添加成功',
            'holiday': holiday.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/personal-holidays/<int:holiday_id>', methods=['PUT'])
def update_personal_holiday(holiday_id):
    """更新个性化节日"""
    try:
        data = request.get_json()
        session_id = get_user_session_id()
        
        holiday = PersonalHoliday.query.filter_by(
            id=holiday_id,
            session_id=session_id
        ).first()
        
        if not holiday:
            return jsonify({'error': '节日不存在或无权限修改'}), 404
        
        # 更新字段
        for field in ['name', 'description', 'month', 'day', 'year', 
                     'category', 'color', 'icon', 'is_birthday', 
                     'is_recurring', 'remind_days_before']:
            if field in data:
                setattr(holiday, field, data[field])
        
        holiday.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '个性化节日更新成功',
            'holiday': holiday.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/personal-holidays/<int:holiday_id>', methods=['DELETE'])
def delete_personal_holiday(holiday_id):
    """删除个性化节日"""
    try:
        session_id = get_user_session_id()
        print(f"[DELETE] Holiday ID: {holiday_id}, Session ID: {session_id}")
        
        holiday = PersonalHoliday.query.filter_by(
            id=holiday_id,
            session_id=session_id
        ).first()
        
        if not holiday:
            print(f"[DELETE] Holiday not found or no permission - ID: {holiday_id}, Session: {session_id}")
            return jsonify({'error': '节日不存在或无权限删除'}), 404
        
        print(f"[DELETE] Found holiday: {holiday.name}, deleting...")
        db.session.delete(holiday)
        db.session.commit()
        print(f"[DELETE] Holiday deleted successfully: {holiday.name}")
        
        return jsonify({
            'success': True,
            'message': '个性化节日删除成功'
        })
        
    except Exception as e:
        print(f"[DELETE] Error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/holiday-templates')
def get_holiday_templates():
    """获取节日模板"""
    try:
        templates = HolidayTemplate.query.all()
        
        return jsonify({
            'success': True,
            'templates': [template.to_dict() for template in templates]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/api/personal-holidays/bulk', methods=['POST'])
def bulk_add_personal_holidays():
    """批量添加个性化节日"""
    try:
        data = request.get_json()
        holidays_data = data.get('holidays', [])
        session_id = get_user_session_id()
        
        added_holidays = []
        
        for holiday_data in holidays_data:
            if not all(k in holiday_data for k in ['name', 'month', 'day']):
                continue
                
            holiday = PersonalHoliday(
                session_id=session_id,
                name=holiday_data['name'],
                description=holiday_data.get('description', ''),
                month=int(holiday_data['month']),
                day=int(holiday_data['day']),
                year=holiday_data.get('year'),
                category=holiday_data.get('category', 'personal'),
                color=holiday_data.get('color', '#ff6b6b'),
                icon=holiday_data.get('icon', '🎉'),
                is_birthday=holiday_data.get('is_birthday', False),
                is_recurring=holiday_data.get('is_recurring', True)
            )
            
            db.session.add(holiday)
            added_holidays.append(holiday)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功添加{len(added_holidays)}个个性化节日',
            'holidays': [h.to_dict() for h in added_holidays]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 初始化数据库表和模板数据
def init_database():
    """初始化数据库表"""
    try:
        db.create_all()
        init_holiday_templates(db)
    except Exception as e:
        print(f"Database initialization error: {e}")
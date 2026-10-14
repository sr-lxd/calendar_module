"""
Calendar Engine - Core calendar generation logic
Adapted from universal_calendar_generator.py for Sofia System
"""

import calendar
import datetime
from collections import defaultdict
import json
import io
from io import BytesIO

# PDF generation imports
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm, mm
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
    PDF_LIBRARY = 'reportlab'
except ImportError as e:
    print(f"ReportLab not available: {e}")
    try:
        from fpdf import FPDF
        REPORTLAB_AVAILABLE = False
        FPDF_AVAILABLE = True
        PDF_LIBRARY = 'fpdf'
        print("Using FPDF as PDF library")
    except ImportError as e2:
        print(f"FPDF also not available: {e2}")
        REPORTLAB_AVAILABLE = False
        FPDF_AVAILABLE = False
        PDF_LIBRARY = None
        print("No PDF library available")
except Exception as e:
    print(f"ReportLab import error: {e}")
    try:
        from fpdf import FPDF
        REPORTLAB_AVAILABLE = False
        FPDF_AVAILABLE = True
        PDF_LIBRARY = 'fpdf'
        print("Using FPDF as fallback PDF library")
    except ImportError:
        REPORTLAB_AVAILABLE = False
        FPDF_AVAILABLE = False
        PDF_LIBRARY = None
        print("No PDF library available")

class CalendarGenerator:
    def __init__(self):
        # Set calendar to start with Sunday (Chinese convention)
        calendar.setfirstweekday(calendar.SUNDAY)
        
        # Load festival and configuration data
        self.load_data()
    
    def load_data(self):
        """Load festival and configuration data"""
        # Traditional festivals
        self.chinese_festivals = {
            "01-01": "元旦",
            "02-14": "情人节", 
            "03-08": "妇女节",
            "03-12": "植树节",
            "04-01": "愚人节",
            "05-01": "劳动节",
            "05-04": "青年节",
            "06-01": "儿童节",
            "07-01": "建党节",
            "08-01": "建军节",
            "09-10": "教师节",
            "10-01": "国庆节",
            "12-25": "圣诞节"
        }
        
        # Lunar festivals mapping
        self.lunar_festivals_2025 = {
            (1, 29): "春节",
            (2, 12): "元宵节",
            (5, 31): "端午节", 
            (8, 29): "七夕节",
            (10, 6): "中秋节",
            (11, 3): "重阳节"
        }
        
        # 24 Solar Terms for 2025
        self.solar_terms_2025 = {
            (1, 5): "小寒", (1, 20): "大寒",
            (2, 3): "立春", (2, 18): "雨水",
            (3, 5): "惊蛰", (3, 20): "春分",
            (4, 4): "清明", (4, 19): "谷雨",
            (5, 5): "立夏", (5, 21): "小满",
            (6, 5): "芒种", (6, 21): "夏至",
            (7, 7): "小暑", (7, 22): "大暑",
            (8, 7): "立秋", (8, 23): "处暑",
            (9, 7): "白露", (9, 22): "秋分",
            (10, 8): "寒露", (10, 23): "霜降",
            (11, 7): "立冬", (11, 22): "小雪",
            (12, 7): "大雪", (12, 21): "冬至"
        }
        
        # Traditional auspicious day components
        self.TIANGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        self.DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
        self.TWELVE_STARS = ['建', '除', '满', '平', '定', '执', '破', '危', '成', '收', '开', '闭']
        self.ZODIAC_GODS = ['青龙', '明堂', '天刑', '朱雀', '金匮', '天德', '白虎', '玉堂', '天牢', '元武', '司命', '勾陈']
        
        # Traditional activity rules
        self.star_rules = {
            '建': (['出行', '上任', '会友', '上书', '见贵'], ['动土', '开仓', '掘井', '造船']),
            '除': (['治病', '捕捉', '扫舍', '祭祀'], ['求官', '上任', '嫁娶', '移徙']),
            '满': (['祈福', '祭祀', '结亲', '开光'], ['服药', '针灸', '栽种', '葬埋']),
            '平': (['修路', '平整', '涂泥', '整容'], ['祭祀', '开光', '嫁娶', '开市']),
            '定': (['嫁娶', '立约', '交易', '纳采'], ['诉讼', '出行', '移徙', '开光']),
            '执': (['建屋', '种植', '捕捉', '纳畜'], ['移徙', '出行', '开市', '立券']),
            '破': (['破屋', '求医', '捕猎', '解除'], ['嫁娶', '开市', '交易', '出行']),
            '危': (['祭祀', '祈福', '斋醮', '立约'], ['登高', '行船', '安床', '作灶']),
            '成': (['开市', '交易', '开光', '修造'], ['嫁娶', '安葬', '栽种', '作灶']),
            '收': (['纳财', '开仓', '嫁娶', '纳采'], ['开市', '立券', '安葬', '栽种']),
            '开': (['开光', '出行', '交易', '嫁娶'], ['葬埋', '开仓', '建屋', '作灶']),
            '闭': (['祭祀', '筑堤', '填穴', '修墓'], ['开市', '出行', '嫁娶', '开光'])
        }
    
    def generate_calendar_data(self, year, options, session_id=None):
        """Generate complete calendar data for a year"""
        calendar_data = {
            'year': year,
            'months': []
        }
        
        for month in range(1, 13):
            month_data = self.generate_month_data(year, month, options, session_id)
            calendar_data['months'].append(month_data)
        
        return calendar_data
    
    def generate_month_data(self, year, month, options, session_id=None):
        """Generate data for a single month"""
        month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                      "七月", "八月", "九月", "十月", "十一月", "十二月"]
        
        cal_matrix = calendar.monthcalendar(year, month)
        today = datetime.date.today()
        
        month_data = {
            'month': month,
            'name': month_names[month],
            'weeks': []
        }
        
        for week in cal_matrix:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append(None)  # Empty cell
                else:
                    day_data = self.generate_day_data(year, month, day, options, today, session_id)
                    week_data.append(day_data)
            month_data['weeks'].append(week_data)
        
        return month_data
    
    def generate_day_data(self, year, month, day, options, today, session_id=None):
        """Generate data for a single day"""
        date_obj = datetime.date(year, month, day)
        date_key = f"{month:02d}-{day:02d}"
        
        day_data = {
            'day': day,
            'date': date_obj.isoformat(),
            'is_today': date_obj == today,
            'is_weekend': date_obj.weekday() in [5, 6],
            'events': []
        }
        
        # Add festival information
        if options.get('show_festivals', False):
            if date_key in self.chinese_festivals:
                day_data['events'].append({
                    'type': 'festival',
                    'name': self.chinese_festivals[date_key]
                })
        
        # Add personal holidays
        if options.get('show_personal_holidays', True):
            try:
                from flask import current_app
                from extensions import db
                from sqlalchemy import text
                
                # Use SQLAlchemy connection from the app with proper parameterized query
                try:
                    query = text("""
                        SELECT name, description, category, color, icon, is_birthday
                        FROM personal_holidays 
                        WHERE month = :month AND day = :day AND is_active = 1
                        AND (session_id = :session_id OR session_id IS NULL)
                    """)
                    
                    result = db.session.execute(query, {
                        'month': month, 
                        'day': day, 
                        'session_id': session_id or 'default'
                    })
                    holidays = result.fetchall()
                    
                    for holiday_data in holidays:
                        name, description, category, color, icon, is_birthday = holiday_data
                        day_data['events'].append({
                            'type': 'personal_holiday',
                            'name': name,
                            'description': description or '',
                            'category': category or 'personal',
                            'color': color or '#ff6b6b',
                            'icon': icon or '🎉',
                            'is_birthday': bool(is_birthday)
                        })
                    
                    # Debug logging
                    if holidays:
                        print(f"Found {len(holidays)} personal holidays for {month:02d}-{day:02d} with session {session_id}")
                    
                except Exception as db_error:
                    print(f"Database error loading personal holidays for {month:02d}-{day:02d}: {db_error}")
                    
            except Exception as e:
                print(f"Error loading personal holidays: {e}")
        
        # Add lunar information
        if options.get('show_lunar', False):
            lunar_info = self.get_lunar_date(year, month, day)
            if lunar_info:
                day_data['events'].append({
                    'type': 'lunar',
                    'name': lunar_info
                })
        
        # Add lunar festivals
        if options.get('show_lunar_festivals', False):
            lunar_festival = self.get_lunar_festival(year, month, day)
            if lunar_festival:
                day_data['events'].append({
                    'type': 'lunar_festival',
                    'name': lunar_festival
                })
        
        # Add solar terms
        if options.get('show_solar_terms', False):
            solar_term = self.get_solar_term(year, month, day)
            if solar_term:
                day_data['events'].append({
                    'type': 'solar_term',
                    'name': solar_term
                })
        
        # Add auspicious information
        if options.get('show_auspicious', False):
            auspicious = self.get_auspicious_info(year, month, day)
            if auspicious and auspicious.get('summary'):
                day_data['events'].append({
                    'type': 'auspicious',
                    'name': auspicious['summary'],
                    'details': auspicious
                })
        
        return day_data
    
    def get_ganzhi_day(self, year, month, day):
        """Calculate Heavenly Stems and Earthly Branches for a date"""
        base_date = datetime.date(1900, 1, 31)  # 甲子日基准
        target_date = datetime.date(year, month, day)
        days_diff = (target_date - base_date).days
        
        ganzhi_index = days_diff % 60
        tian = ganzhi_index % 10
        di = ganzhi_index % 12
        
        return self.TIANGAN[tian] + self.DIZHI[di], ganzhi_index
    
    def get_twelve_star(self, lunar_month, lunar_day, ganzhi_index):
        """Get Twelve Stars for a date"""
        star_index = (lunar_month + lunar_day + ganzhi_index) % 12
        return self.TWELVE_STARS[star_index]
    
    def get_zodiac_god(self, ganzhi_index):
        """Get Zodiac God for a date"""
        return self.ZODIAC_GODS[ganzhi_index % 12]
    
    def get_auspicious_info(self, year, month, day):
        """Get comprehensive traditional auspicious day information"""
        try:
            # 获取精确的农历日期
            lunar_info = self.get_precise_lunar_info(year, month, day)
            
            # Calculate complete Ganzhi system (年月日时)
            ganzhi_info = self.get_complete_ganzhi(year, month, day)
            
            # Calculate traditional elements
            star = self.get_twelve_star_precise(lunar_info['month'], lunar_info['day'], ganzhi_info['day_index'])
            god = self.get_zodiac_god_precise(ganzhi_info['day_index'])
            
            # Calculate additional traditional elements
            chong_sha = self.get_chong_sha(ganzhi_info['day_branch'])
            peng_zu = self.get_peng_zu_baiji(ganzhi_info['day_stem'], ganzhi_info['day_branch'])
            tai_shen = self.get_tai_shen_position(lunar_info['month'], lunar_info['day'])
            
            # Get comprehensive activities recommendations
            yi_items, ji_items = self.get_comprehensive_activities(
                star, god, ganzhi_info, lunar_info, year, month, day
            )
            
            # Calculate auspicious level
            auspicious_level = self.calculate_auspicious_level(star, god, ganzhi_info)
            
            return {
                'ganzhi': ganzhi_info['day_ganzhi'],
                'year_ganzhi': ganzhi_info['year_ganzhi'],
                'month_ganzhi': ganzhi_info['month_ganzhi'],
                'star': star,
                'god': god,
                'lunar_info': lunar_info,
                'chong_sha': chong_sha,
                'peng_zu': peng_zu,
                'tai_shen': tai_shen,
                'auspicious_level': auspicious_level,
                'yi': yi_items,
                'ji': ji_items,
                'yi_text': self.format_items_text(yi_items[:3]),
                'ji_text': self.format_items_text(ji_items[:3]),
                'summary': f"{auspicious_level['level']}",
                'detailed_summary': self.format_detailed_summary(yi_items, ji_items, auspicious_level)
            }
            
        except Exception as e:
            print(f"Error in auspicious calculation: {e}")
            return {'yi': [], 'ji': [], 'summary': ''}
    
    def get_precise_lunar_info(self, year, month, day):
        """Get precise lunar calendar information"""
        try:
            import lunardate
            lunar = lunardate.LunarDate.fromSolarDate(year, month, day)
            return {
                'year': lunar.year,
                'month': lunar.month,
                'day': lunar.day,
                'is_leap': lunar.isLeapMonth if hasattr(lunar, 'isLeapMonth') else False
            }
        except:
            # Fallback to estimation
            return {'year': year, 'month': month, 'day': day, 'is_leap': False}
    
    def get_complete_ganzhi(self, year, month, day):
        """Calculate complete Ganzhi for year, month, day"""
        # Year Ganzhi (starting from 1900 = 庚子年)
        year_index = (year - 1900) % 60
        year_stem = year_index % 10
        year_branch = year_index % 12
        year_ganzhi = self.TIANGAN[year_stem] + self.DIZHI[year_branch]
        
        # Month Ganzhi (based on year stem and solar terms)
        month_index = self.get_month_ganzhi_index(year, month, day)
        month_stem = month_index % 10
        month_branch = month_index % 12
        month_ganzhi = self.TIANGAN[month_stem] + self.DIZHI[month_branch]
        
        # Day Ganzhi (more precise calculation)
        day_ganzhi, day_index = self.get_ganzhi_day(year, month, day)
        day_stem = day_index % 10
        day_branch = day_index % 12
        
        return {
            'year_ganzhi': year_ganzhi,
            'year_stem': self.TIANGAN[year_stem],
            'year_branch': self.DIZHI[year_branch],
            'month_ganzhi': month_ganzhi,
            'month_stem': self.TIANGAN[month_stem],
            'month_branch': self.DIZHI[month_branch],
            'day_ganzhi': day_ganzhi,
            'day_stem': self.TIANGAN[day_stem],
            'day_branch': self.DIZHI[day_branch],
            'day_index': day_index
        }
    
    def get_month_ganzhi_index(self, year, month, day):
        """Calculate month Ganzhi index based on solar terms"""
        # Simplified month Ganzhi calculation
        # In real implementation, this should be based on solar terms
        year_stem = ((year - 1900) % 60) % 10
        base_month = month + 12 * year_stem
        return base_month % 60
    
    def get_twelve_star_precise(self, lunar_month, lunar_day, ganzhi_index):
        """Get Twelve Stars using precise lunar calendar"""
        star_index = (lunar_month + lunar_day + ganzhi_index) % 12
        return self.TWELVE_STARS[star_index]
    
    def get_zodiac_god_precise(self, ganzhi_index):
        """Get Zodiac God with enhanced calculation"""
        return self.ZODIAC_GODS[ganzhi_index % 12]
    
    def get_chong_sha(self, day_branch):
        """Calculate conflicting zodiac and direction"""
        branch_index = self.DIZHI.index(day_branch)
        # 相冲关系：子午冲、丑未冲、寅申冲、卯酉冲、辰戌冲、巳亥冲
        chong_pairs = {
            0: (6, '午', '南方'),   # 子冲午
            1: (7, '未', '西南'),  # 丑冲未
            2: (8, '申', '西南'),  # 寅冲申
            3: (9, '酉', '西方'),  # 卯冲酉
            4: (10, '戌', '西北'), # 辰冲戌
            5: (11, '亥', '西北'), # 巳冲亥
            6: (0, '子', '北方'),  # 午冲子
            7: (1, '丑', '东北'),  # 未冲丑
            8: (2, '寅', '东北'),  # 申冲寅
            9: (3, '卯', '东方'),  # 酉冲卯
            10: (4, '辰', '东南'), # 戌冲辰
            11: (5, '巳', '东南')  # 亥冲巳
        }
        
        if branch_index in chong_pairs:
            _, chong_branch, direction = chong_pairs[branch_index]
            return f"冲{chong_branch} 煞{direction}"
        return "无冲煞"
    
    def get_peng_zu_baiji(self, day_stem, day_branch):
        """Calculate Pengzu taboos"""
        stem_index = self.TIANGAN.index(day_stem)
        branch_index = self.DIZHI.index(day_branch)
        
        # 彭祖百忌表
        stem_taboos = [
            "甲不开仓财物耗散", "乙不栽植千株不长", "丙不修灶必见灾殃", "丁不剃头头必生疮",
            "戊不受田田主不祥", "己不破券二比并亡", "庚不经络织机虚张", "辛不合酱主人不尝",
            "壬不泱水更难提防", "癸不词讼理弱敌强"
        ]
        
        branch_taboos = [
            "子不问卜自惹祸殃", "丑不冠带主不还乡", "寅不祭祀神鬼不尝", "卯不穿井水泉不香",
            "辰不哭泣必主重丧", "巳不远行财物伏藏", "午不苫盖屋主更张", "未不服药毒气入肠",
            "申不安床鬼祟入房", "酉不会客醉坐颠狂", "戌不吃犬作怪上床", "亥不嫁娶不利新郎"
        ]
        
        return {
            'stem_taboo': stem_taboos[stem_index],
            'branch_taboo': branch_taboos[branch_index]
        }
    
    def get_tai_shen_position(self, lunar_month, lunar_day):
        """Calculate Tai Shen (fetus god) position"""
        # 胎神位置计算（简化版）
        positions = [
            "房床门", "碓磨门", "厨灶炉", "仓库门", "房床栖", "占门床",
            "厨灶碓", "仓库厨", "房床门", "碓磨栖", "厨灶炉", "仓库碓",
            "房床厨", "碓磨炉", "厨灶门", "仓库床", "占房栖", "碓磨门",
            "厨灶碓", "仓库炉", "房床厨", "碓磨床", "厨灶栖", "仓库门",
            "占房碓", "碓磨炉", "厨灶床", "仓库栖", "房床门", "碓磨厨"
        ]
        
        directions = ["东", "南", "西", "北", "中"]
        day_index = (lunar_day - 1) % len(positions)
        direction_index = (lunar_month + lunar_day) % len(directions)
        
        return f"{positions[day_index]}{directions[direction_index]}外"
    
    def calculate_auspicious_level(self, star, god, ganzhi_info):
        """Calculate overall auspicious level"""
        score = 50  # Base score
        
        # Adjust based on twelve stars
        star_scores = {
            '建': 85, '除': 70, '满': 75, '平': 60, '定': 80, '执': 65,
            '破': 30, '危': 40, '成': 80, '收': 75, '开': 85, '闭': 45
        }
        
        # Adjust based on zodiac gods
        god_scores = {
            '青龙': 90, '明堂': 85, '天刑': 35, '朱雀': 40, '金匮': 80, '天德': 95,
            '白虎': 25, '玉堂': 80, '天牢': 30, '元武': 35, '司命': 85, '勾陈': 45
        }
        
        if star in star_scores:
            score = (score + star_scores[star]) // 2
        
        if god in god_scores:
            score = (score + god_scores[god]) // 2
        
        # Convert to level description
        if score >= 80:
            return {'level': '大吉', 'score': score, 'color': 'success'}
        elif score >= 65:
            return {'level': '中吉', 'score': score, 'color': 'info'}
        elif score >= 45:
            return {'level': '小吉', 'score': score, 'color': 'warning'}
        else:
            return {'level': '不宜', 'score': score, 'color': 'danger'}
    
    def get_comprehensive_activities(self, star, god, ganzhi_info, lunar_info, year, month, day):
        """Get comprehensive activity recommendations"""
        yi_items = []
        ji_items = []
        
        # Base activities from star rules
        if star in self.star_rules:
            base_yi, base_ji = self.star_rules[star]
            yi_items.extend(base_yi)
            ji_items.extend(base_ji)
        
        # Enhanced activities based on zodiac gods
        god_enhancements = self.get_god_activity_enhancements(god)
        yi_items.extend(god_enhancements['yi'])
        ji_items.extend(god_enhancements['ji'])
        
        # Seasonal adjustments
        seasonal_adjustments = self.get_seasonal_adjustments(month)
        yi_items.extend(seasonal_adjustments['yi'])
        ji_items.extend(seasonal_adjustments['ji'])
        
        # Lunar phase adjustments
        lunar_adjustments = self.get_lunar_phase_adjustments(lunar_info['day'])
        yi_items.extend(lunar_adjustments['yi'])
        ji_items.extend(lunar_adjustments['ji'])
        
        # Five elements interactions
        wuxing_adjustments = self.get_wuxing_adjustments(ganzhi_info)
        yi_items.extend(wuxing_adjustments['yi'])
        ji_items.extend(wuxing_adjustments['ji'])
        
        # Remove duplicates and categorize
        yi_items = list(dict.fromkeys(yi_items))
        ji_items = list(dict.fromkeys(ji_items))
        
        # Add detailed descriptions
        yi_detailed = self.add_activity_descriptions(yi_items, 'yi')
        ji_detailed = self.add_activity_descriptions(ji_items, 'ji')
        
        return yi_detailed[:8], ji_detailed[:6]  # Limit for display
    
    def get_god_activity_enhancements(self, god):
        """Enhanced activity recommendations based on zodiac gods"""
        god_activities = {
            '青龙': {
                'yi': ['求财', '开市', '交易', '签约', '出行', '求职', '投资', '合作'],
                'ji': ['争讼', '动怒', '冲动决策']
            },
            '明堂': {
                'yi': ['上任', '求官', '拜访贵人', '学习', '考试', '开业', '庆典'],
                'ji': ['隐瞒', '欺骗', '暗中行事']
            },
            '天刑': {
                'yi': ['执法', '断案', '清理', '整顿'],
                'ji': ['嫁娶', '庆祝', '开业', '合作', '签约']
            },
            '朱雀': {
                'yi': ['文书', '考试', '学习', '写作', '宣传'],
                'ji': ['口舌争执', '诽谤', '造谣']
            },
            '金匮': {
                'yi': ['存钱', '理财', '收账', '谈判', '签约', '投资'],
                'ji': ['借贷', '挥霍', '冒险投机']
            },
            '天德': {
                'yi': ['祈福', '行善', '捐赠', '拜神', '许愿', '求子', '治病'],
                'ji': ['作恶', '欺人', '伤害']
            },
            '白虎': {
                'yi': ['清除', '分离', '断舍离', '治病'],
                'ji': ['嫁娶', '开业', '庆典', '投资', '合作']
            },
            '玉堂': {
                'yi': ['文艺', '创作', '装修', '美化', '社交', '娱乐'],
                'ji': ['粗俗', '破坏', '争斗']
            },
            '天牢': {
                'yi': ['静思', '反省', '整理', '修复'],
                'ji': ['出行', '开业', '签约', '投资', '嫁娶']
            },
            '元武': {
                'yi': ['隐匿', '保密', '内省', '修养'],
                'ji': ['公开', '张扬', '冒险', '急进']
            },
            '司命': {
                'yi': ['求医', '养生', '祈福', '行善', '救助'],
                'ji': ['伤害', '冒险', '不义之财']
            },
            '勾陈': {
                'yi': ['谨慎', '保守', '维持', '守成'],
                'ji': ['冒进', '变动', '扩张', '投机']
            }
        }
        
        return god_activities.get(god, {'yi': [], 'ji': []})
    
    def get_seasonal_adjustments(self, month):
        """Seasonal activity adjustments"""
        seasonal_activities = {
            # 春季 (3-5月)
            'spring': {
                'months': [3, 4, 5],
                'yi': ['种植', '播种', '开始新项目', '求职', '搬迁', '装修'],
                'ji': ['大兴土木', '重大手术']
            },
            # 夏季 (6-8月)
            'summer': {
                'months': [6, 7, 8],
                'yi': ['旅游', '外出', '运动', '社交', '庆典'],
                'ji': ['长途搬迁', '重大变动']
            },
            # 秋季 (9-11月)
            'autumn': {
                'months': [9, 10, 11],
                'yi': ['收获', '收账', '储蓄', '总结', '整理'],
                'ji': ['大规模种植', '冒险投资']
            },
            # 冬季 (12, 1, 2月)
            'winter': {
                'months': [12, 1, 2],
                'yi': ['休养', '学习', '总结', '计划', '内修'],
                'ji': ['大动', '远行', '露天作业']
            }
        }
        
        for season_data in seasonal_activities.values():
            if month in season_data['months']:
                return {'yi': season_data['yi'], 'ji': season_data['ji']}
        
        return {'yi': [], 'ji': []}
    
    def get_lunar_phase_adjustments(self, lunar_day):
        """Lunar phase based adjustments"""
        if 1 <= lunar_day <= 7:  # 新月期
            return {
                'yi': ['开始', '计划', '种植', '求学'],
                'ji': ['收割', '完结', '分离']
            }
        elif 8 <= lunar_day <= 14:  # 上弦月
            return {
                'yi': ['发展', '扩张', '推进', '合作'],
                'ji': ['急躁', '冲动', '草率决定']
            }
        elif 15 <= lunar_day <= 22:  # 满月期
            return {
                'yi': ['庆祝', '完成', '收获', '成交'],
                'ji': ['开始新项目', '播种']
            }
        else:  # 下弦月
            return {
                'yi': ['整理', '清理', '反思', '休息'],
                'ji': ['开始', '扩张', '冒险']
            }
    
    def get_wuxing_adjustments(self, ganzhi_info):
        """Five elements based adjustments"""
        # 天干五行
        stem_wuxing = {
            '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
            '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'
        }
        
        # 地支五行
        branch_wuxing = {
            '子': '水', '丑': '土', '寅': '木', '卯': '木', '辰': '土', '巳': '火',
            '午': '火', '未': '土', '申': '金', '酉': '金', '戌': '土', '亥': '水'
        }
        
        day_stem_element = stem_wuxing.get(ganzhi_info['day_stem'], '')
        day_branch_element = branch_wuxing.get(ganzhi_info['day_branch'], '')
        
        # 五行对应的活动建议
        element_activities = {
            '木': {
                'yi': ['创新', '发展', '学习', '种植', '文艺创作'],
                'ji': ['砍伐', '破坏', '过度竞争']
            },
            '火': {
                'yi': ['庆典', '宣传', '演出', '运动', '光明正大的事'],
                'ji': ['争斗', '冲突', '过于激进']
            },
            '土': {
                'yi': ['建设', '储蓄', '稳固', '农事', '房地产'],
                'ji': ['冒险', '投机', '急进']
            },
            '金': {
                'yi': ['收获', '整理', '金融', '机械', '精确工作'],
                'ji': ['浪费', '粗糙', '不精确']
            },
            '水': {
                'yi': ['学习', '思考', '流动', '清洁', '适应变化'],
                'ji': ['固执', '僵化', '过度消费']
            }
        }
        
        yi_activities = []
        ji_activities = []
        
        if day_stem_element in element_activities:
            yi_activities.extend(element_activities[day_stem_element]['yi'])
            ji_activities.extend(element_activities[day_stem_element]['ji'])
        
        return {'yi': yi_activities, 'ji': ji_activities}
    
    def add_activity_descriptions(self, activities, activity_type):
        """Add detailed descriptions to activities"""
        detailed_descriptions = {
            # 宜事详解
            '祈福': '向神明祈求福佑，宜烧香拜佛，许愿还愿',
            '嫁娶': '举行婚礼，宜选择良辰吉日，百年好合',
            '出行': '外出旅行或办事，宜选择良好方向，平安顺利',
            '开市': '开张营业或新店开业，宜选择吉时，生意兴隆',
            '立券': '签订合同契约，宜慎重考虑，诚信为本',
            '交易': '买卖交换，宜公平公正，互利互惠',
            '纳财': '收入财物或投资理财，宜谨慎理财，积少成多',
            '求嗣': '祈求子嗣或备孕，宜调养身体，顺其自然',
            '安葬': '埋葬先人，宜选择风水宝地，慎终追远',
            '修造': '建设或修缮房屋，宜规划周全，注意安全',
            '种植': '播种栽培植物，宜选择合适季节，精心照料',
            '学习': '求学进修，宜专心致志，持之以恒',
            '治病': '医疗保健，宜遵医嘱，调养身心',
            '搬迁': '迁移居所，宜选择良辰，顺利安居',
            '签约': '签署重要合同，宜仔细阅读，慎重决定',
            '投资': '资金投入，宜理性分析，控制风险',
            '合作': '与他人协作，宜诚信相待，互利共赢',
            '求职': '寻找工作机会，宜主动积极，展示才能',
            '庆典': '举行庆祝活动，宜热情有序，分享喜悦',
            '社交': '人际交往活动，宜真诚待人，广结善缘',
            
            # 忌事详解
            '动土': '挖掘土地或建筑施工，今日不宜，恐有不利',
            '开仓': '开启仓库或大量支出，今日不宜，恐财物损失',
            '出师': '出兵征战或开始争斗，今日不宜，恐有损伤',
            '词讼': '打官司或法律纠纷，今日不宜，恐败诉或纠缠',
            '移徙': '搬家或迁移，今日不宜，恐不安定',
            '入宅': '迁入新居，今日不宜，恐不顺利',
            '安床': '安置床铺，今日不宜，恐睡眠不安',
            '开光': '开启神像光明，今日不宜，恐不灵验',
            '作灶': '建造厨灶，今日不宜，恐火灾或不利',
            '栽种': '种植农作物，今日不宜，恐不易成活',
            '争讼': '争论诉讼，今日不宜，恐败诉或损失',
            '冲动决策': '草率决定重要事项，今日不宜，恐后悔',
            '借贷': '借钱或放贷，今日不宜，恐有损失',
            '冒险投机': '高风险投资，今日不宜，恐血本无归',
            '大动': '大规模行动或变动，今日不宜，恐不稳定',
            '急进': '急于求成或冒进，今日不宜，恐适得其反'
        }
        
        result = []
        for activity in activities:
            if activity in detailed_descriptions:
                result.append({
                    'name': activity,
                    'description': detailed_descriptions[activity],
                    'type': activity_type
                })
            else:
                result.append({
                    'name': activity,
                    'description': f"{'宜' if activity_type == 'yi' else '忌'}{activity}",
                    'type': activity_type
                })
        
        return result
    
    def format_detailed_summary(self, yi_items, ji_items, auspicious_level):
        """Format detailed summary with level information"""
        level_desc = auspicious_level['level']
        yi_names = [item['name'] if isinstance(item, dict) else item for item in yi_items[:3]]
        ji_names = [item['name'] if isinstance(item, dict) else item for item in ji_items[:3]]
        
        yi_text = ' '.join(yi_names) if yi_names else "诸事不宜"
        ji_text = ' '.join(ji_names) if ji_names else "无特别禁忌"
        
        return f"【{level_desc}】宜: {yi_text} | 忌: {ji_text}"
    
    def format_items_text(self, items):
        """Format items list to text string"""
        if not items:
            return "诸事不宜" if items == [] else "无特别禁忌"
        
        item_names = []
        for item in items:
            if isinstance(item, dict) and 'name' in item:
                item_names.append(item['name'])
            else:
                item_names.append(str(item))
        
        return ' '.join(item_names) if item_names else "诸事不宜"
    
    def get_activities_by_star_and_god(self, star, god, ganzhi_index):
        """Determine suitable/unsuitable activities based on star and god"""
        yi_items = []
        ji_items = []
        
        # Apply traditional star rules
        if star in self.star_rules:
            yi_items, ji_items = self.star_rules[star]
        
        # Adjust based on zodiac god
        if god in ['青龙', '明堂', '金匮', '天德', '玉堂', '司命']:  # Auspicious gods
            yi_items = list(yi_items) + ['祈福', '求嗣', '上官', '纳财']
        else:  # Inauspicious gods
            ji_items = list(ji_items) + ['重要决策', '签约', '开业']
        
        # Remove duplicates and limit quantity
        yi_items = list(dict.fromkeys(yi_items))[:6]
        ji_items = list(dict.fromkeys(ji_items))[:4]
        
        return yi_items, ji_items
    
    def get_lunar_date(self, year, month, day):
        """Get lunar calendar date using accurate lunardate library"""
        try:
            import lunardate
            
            # Use lunardate library for accurate conversion
            lunar = lunardate.LunarDate.fromSolarDate(year, month, day)
            lunar_month = lunar.month
            lunar_day = lunar.day
            
            # Format lunar date names
            lunar_months = ["", "正月", "二月", "三月", "四月", "五月", "六月",
                           "七月", "八月", "九月", "十月", "十一月", "十二月"]
            lunar_days = ["", "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
                         "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                         "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
            
            return f"{lunar_months[lunar_month]}{lunar_days[lunar_day]}"
            
        except ImportError:
            # Fallback to simplified estimation if lunardate is not available
            return self._get_lunar_date_fallback(year, month, day)
        except Exception as e:
            print(f"Error in lunar date calculation: {e}")
            return ""
    
    def _get_lunar_date_fallback(self, year, month, day):
        """Fallback lunar date calculation (simplified estimation)"""
        try:
            # For 2025, use known data points
            if year == 2025:
                spring_festival = datetime.date(2025, 1, 29)
                current_date = datetime.date(year, month, day)
                days_diff = (current_date - spring_festival).days
                
                # Estimate lunar month and day
                estimated_lunar_month = 1 + (days_diff // 30)
                estimated_lunar_day = (days_diff % 30) + 1
                
                # Adjust ranges
                while estimated_lunar_month > 12:
                    estimated_lunar_month -= 12
                while estimated_lunar_month < 1:
                    estimated_lunar_month += 12
                
                estimated_lunar_day = max(1, min(30, estimated_lunar_day))
                
                # Format lunar date names
                lunar_months = ["", "正月", "二月", "三月", "四月", "五月", "六月",
                               "七月", "八月", "九月", "十月", "十一月", "十二月"]
                lunar_days = ["", "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
                             "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                             "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
                
                return f"{lunar_months[estimated_lunar_month]}{lunar_days[estimated_lunar_day]}"
            
            return ""
        except:
            return ""
    
    def get_lunar_festival(self, year, month, day):
        """Get lunar festival for a date"""
        if year == 2025:
            return self.lunar_festivals_2025.get((month, day), "")
        return ""
    
    def get_solar_term(self, year, month, day):
        """Get solar term for a date using precise calculation with Beijing time"""
        try:
            import sxtwl
            
            # 使用sxtwl库进行精确计算
            day_obj = sxtwl.fromSolar(year, month, day)
            jieqi_code = day_obj.getJieQi()
            
            if jieqi_code is not None and jieqi_code != 255:  # 255表示无节气，0是有效的节气编码
                # 节气名称映射表 (基于sxtwl库的编码)
                jieqi_names = [
                    '冬至', '小寒', '大寒', '立春', '雨水', '惊蛰', '春分',
                    '清明', '谷雨', '立夏', '小满', '芒种', '夏至',
                    '小暑', '大暑', '立秋', '处暑', '白露', '秋分',
                    '寒露', '霜降', '立冬', '小雪', '大雪'
                ]
                
                if 0 <= jieqi_code < len(jieqi_names):
                    return jieqi_names[jieqi_code]
            
            return ""
            
        except ImportError:
            # Fallback to static data if sxtwl is not available
            return self._get_solar_term_fallback(year, month, day)
        except Exception as e:
            print(f"Error in solar term calculation: {e}")
            return ""
    
    def _get_solar_term_fallback(self, year, month, day):
        """Fallback solar term calculation using static data"""
        if year == 2025:
            return self.solar_terms_2025.get((month, day), "")
        return ""
    
    def get_lunar_info(self, year, month, day):
        """Get complete lunar information for a date"""
        return {
            'lunar_date': self.get_lunar_date(year, month, day),
            'lunar_festival': self.get_lunar_festival(year, month, day),
            'solar_term': self.get_solar_term(year, month, day)
        }
    
    def get_year_festivals(self, year):
        """Get all festivals for a year"""
        festivals = {
            'solar_festivals': self.chinese_festivals,
            'lunar_festivals': self.lunar_festivals_2025 if year == 2025 else {},
            'solar_terms': self.solar_terms_2025 if year == 2025 else {}
        }
        return festivals
    
    def generate_html(self, year, options, session_id=None):
        """Generate HTML calendar"""
        calendar_data = self.generate_calendar_data(year, options, session_id)
        
        # Generate months HTML content
        months_html = self._generate_months_html_content(calendar_data)
        
        # HTML template with modern styling
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{year}年历 - Sofia Calendar</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .calendar-container {{
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            padding: 30px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .year-title {{
            text-align: center;
            font-size: 36px;
            color: #2c3e50;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        .months-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
        }}
        .calendar-month {{
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .month-header {{
            background: linear-gradient(135deg, #17a2b8, #138496);
            color: white;
            text-align: center;
            padding: 12px;
            font-size: 16px;
            font-weight: bold;
        }}
        .weekdays {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}
        .weekday {{
            padding: 8px 4px;
            text-align: center;
            font-weight: bold;
            color: #343a40;
            font-size: 12px;
        }}
        .calendar-days {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 1px;
            background: #f0f0f0;
        }}
        .calendar-day {{
            background: white;
            min-height: 60px;
            padding: 4px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
        }}
        .calendar-day.today {{
            background: #dc3545;
            color: white;
            font-weight: bold;
        }}
        .calendar-day.weekend {{
            background: #fff8e1;
        }}
        .day-number {{
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 2px;
        }}
        .day-events {{
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
            font-size: 8px;
            line-height: 1.1;
        }}
        .day-event {{
            margin: 1px 0;
            padding: 1px 2px;
            border-radius: 2px;
            text-align: center;
            width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .day-event.festival {{
            background: #ffebee;
            color: #dc3545;
            font-weight: bold;
        }}
        .day-event.lunar {{
            background: #e8f5e8;
            color: #28a745;
        }}
        .day-event.lunar_festival {{
            background: #fff3e0;
            color: #ff6f00;
            font-weight: bold;
        }}
        .day-event.solar_term {{
            background: #e3f2fd;
            color: #17a2b8;
            font-weight: bold;
        }}
        .day-event.auspicious {{
            background: #f3e5f5;
            color: #7b1fa2;
            font-weight: bold;
        }}
        .day-event.personal_holiday {{
            background: rgba(255, 107, 107, 0.1);
            border-left: 3px solid #ff6b6b;
            font-weight: 500;
        }}
        .day-event.personal_holiday.birthday-event {{
            background: rgba(255, 105, 180, 0.15);
            border-left-color: #ff69b4;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 14px;
        }}
        @media print {{
            body {{ background: white !important; }}
            .calendar-container {{ box-shadow: none !important; }}
        }}
    </style>
</head>
<body>
    <div class="calendar-container">
        <h1 class="year-title">{year} 年历</h1>
        <div class="months-grid">
            {months_html}
        </div>
        <div class="footer">
            <p>Generated by Sofia Calendar System</p>
        </div>
    </div>
</body>
</html>"""
        return html_template
    
    def _generate_months_html_content(self, calendar_data):
        """Generate HTML content for all months"""
        month_names = [
            "", "一月", "二月", "三月", "四月", "五月", "六月",
            "七月", "八月", "九月", "十月", "十一月", "十二月"
        ]
        
        months_html = ""
        for month_data in calendar_data['months']:
            month_number = month_data['month']
            month_name = month_names[month_number]
            
            # Generate days HTML for this month
            days_html = ""
            for week in month_data['weeks']:
                for day_data in week:
                    if day_data is None:
                        days_html += '<div class="calendar-day"></div>'
                    else:
                        day_classes = ['calendar-day']
                        if day_data.get('is_today'):
                            day_classes.append('today')
                        if day_data.get('is_weekend'):
                            day_classes.append('weekend')
                        
                        events_html = ""
                        for event in day_data.get('events', []):
                            event_class = f"day-event {event['type']}"
                            event_content = event['name']
                            
                            # Handle personal holiday with icon and color
                            if event['type'] == 'personal_holiday':
                                if event.get('icon'):
                                    event_content = f"{event['icon']} {event['name']}"
                                if event.get('is_birthday'):
                                    event_class += ' birthday-event'
                            
                            events_html += f'<div class="{event_class}">{event_content}</div>'
                        
                        days_html += f'''
                            <div class="{' '.join(day_classes)}">
                                <div class="day-number">{day_data['day']}</div>
                                <div class="day-events">{events_html}</div>
                            </div>
                        '''
            
            months_html += f'''
                <div class="calendar-month">
                    <div class="month-header">
                        {month_name} {calendar_data['year']}
                    </div>
                    <div class="weekdays">
                        <div class="weekday">日</div>
                        <div class="weekday">一</div>
                        <div class="weekday">二</div>
                        <div class="weekday">三</div>
                        <div class="weekday">四</div>
                        <div class="weekday">五</div>
                        <div class="weekday">六</div>
                    </div>
                    <div class="calendar-days">
                        {days_html}
                    </div>
                </div>
            '''
        
        return months_html
    
    def generate_pdf(self, year, options, session_id=None):
        """Generate PDF calendar"""
        if PDF_LIBRARY == 'reportlab':
            return self._generate_pdf_reportlab(year, options, session_id)
        elif PDF_LIBRARY == 'fpdf':
            return self._generate_pdf_fpdf(year, options, session_id)
        else:
            print("No PDF library available, using fallback")
            return self._generate_simple_pdf_fallback(year, options, session_id)
    
    def _generate_pdf_reportlab(self, year, options, session_id=None):
        """Generate PDF calendar using ReportLab"""
        try:
            # Create a BytesIO buffer to store PDF
            buffer = BytesIO()
            import os

            calendar_font = 'Helvetica'
            font_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fonts', 'msyh.ttc'),
                'C:/Windows/Fonts/msyh.ttc',
                'C:/Windows/Fonts/simhei.ttf',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            ]
            for font_path in font_paths:
                if not os.path.isfile(font_path):
                    continue
                try:
                    pdfmetrics.registerFont(TTFont('CalendarChinese', font_path, subfontIndex=0))
                    pdfmetrics.registerFontFamily(
                        'CalendarChinese', normal='CalendarChinese', bold='CalendarChinese',
                        italic='CalendarChinese', boldItalic='CalendarChinese'
                    )
                    calendar_font = 'CalendarChinese'
                    break
                except Exception as font_error:
                    print(f"Unable to load calendar font {font_path}: {font_error}")

            # Use a nearly borderless portrait A4 page. All 12 months are
            # arranged in a compact 3-column by 4-row grid.
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=3*mm,
                leftMargin=3*mm,
                topMargin=3*mm,
                bottomMargin=3*mm,
                title=f"{year}年年历"
            )
            
            # Create story list to hold all content
            story = []
            
            # Setup styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                leading=18,
                spaceAfter=0,
                alignment=TA_CENTER,
                fontName=calendar_font,
            )
            
            # Add title
            title_text = f"{year}年年历" if calendar_font != 'Helvetica' else f"{year} Calendar"
            title = Paragraph(title_text, title_style)
            story.append(title)
            story.append(Spacer(1, 4))
            
            # Generate calendar data
            calendar_data = self.generate_calendar_data(year, options, session_id)
            
            # Month names
            month_names = (
                ["", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
                if calendar_font != 'Helvetica'
                else ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            )
            
            # Fit all 12 months on one A4 portrait page.
            month_width = doc.width / 3
            month_tables = [
                self._create_month_table_for_pdf(month_data, year, month_names, month_width - 3, calendar_font)
                for month_data in calendar_data['months']
            ]
            month_grid = [month_tables[index:index + 3] for index in range(0, 12, 3)]
            grid = Table(month_grid, colWidths=[month_width] * 3)
            grid.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 1.5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 1.5),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            story.append(grid)
            
            # Build PDF with error handling
            try:
                doc.build(story)
                print(f"PDF successfully generated for year {year}")
            except Exception as build_error:
                print(f"Error building PDF document: {build_error}")
                raise build_error
            
            # Get PDF content
            pdf_content = buffer.getvalue()
            buffer.close()
            
            if len(pdf_content) < 100:  # Sanity check
                raise Exception(f"Generated PDF too small: {len(pdf_content)} bytes")
            
            print(f"PDF generated successfully, size: {len(pdf_content)} bytes")
            return pdf_content
            
        except Exception as e:
            print(f"Error generating PDF with ReportLab: {e}")
            print("Falling back to simple PDF generation")
            return self._generate_simple_pdf_fallback(year, options, session_id)
    
    def _generate_pdf_fpdf(self, year, options, session_id=None):
        """Generate PDF calendar using FPDF"""
        try:
            # Create FPDF instance with UTF-8 support
            pdf = FPDF(orientation='P', unit='mm', format='A4')  # Portrait A4
            pdf.add_page()
            
            # Try to add Chinese font support
            chinese_font_added = False
            try:
                # Try common Chinese font files
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                font_paths = [
                    # Project fonts directory
                    os.path.join(current_dir, 'static', 'fonts', 'msyh.ttc'),
                    os.path.join(current_dir, 'static', 'fonts', 'simhei.ttf'),
                    # Windows fonts
                    'C:/Windows/Fonts/msyh.ttc',  # Microsoft YaHei
                    'C:/Windows/Fonts/simhei.ttf',  # SimHei
                    'C:/Windows/Fonts/simsun.ttc',  # SimSun
                    # Linux fonts
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                    # Mac fonts
                    '/System/Library/Fonts/PingFang.ttc',
                    '/System/Library/Fonts/Helvetica.ttc',
                ]
                
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            if font_path.endswith('.ttc'):
                                # For TTC fonts, we need to specify font index
                                pdf.add_font('Chinese', '', font_path, uni=True)
                            else:
                                pdf.add_font('Chinese', '', font_path, uni=True)
                            chinese_font_added = True
                            print(f"Successfully added Chinese font: {font_path}")
                            break
                        except Exception as font_error:
                            print(f"Failed to add font {font_path}: {font_error}")
                            continue
                            
                if not chinese_font_added:
                    print("No Chinese font found, using built-in font with Pinyin")
                    
            except Exception as e:
                print(f"Error setting up Chinese font: {e}")
            
            # Generate calendar data
            calendar_data = self.generate_calendar_data(year, options, session_id)
            
            # Month names - provide both Chinese and English
            if chinese_font_added:
                month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                              "七月", "八月", "九月", "十月", "十一月", "十二月"]
            else:
                month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            # Calculate dimensions
            page_width = 210  # A4 portrait width in mm
            page_height = 297  # A4 portrait height in mm
            margin = 2
            usable_width = page_width - 2 * margin
            usable_height = page_height - 16  # compact title area

            month_width = usable_width / 3
            month_height = usable_height / 4
            
            current_month = 0
            
            if chinese_font_added:
                pdf.set_font('Chinese', '', 10)
                pdf.cell(0, 7, f'{year}年年历', 0, 1, 'C')
            else:
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 7, f'{year} Calendar', 0, 1, 'C')

            for page_num in range(1):
                for row in range(4):
                    for col in range(3):
                        if current_month >= 12:
                            break
                        
                        month_data = calendar_data['months'][current_month]
                        month = month_data['month']
                        
                        # Calculate position
                        x = margin + col * month_width
                        y = 10 + row * month_height
                        
                        # Draw month
                        self._draw_month_fpdf(pdf, month_data, month_names[month], year, x, y, month_width, month_height, chinese_font_added)
                        
                        current_month += 1
                    
                    if current_month >= 12:
                        break
            
            # Get PDF content
            pdf_content = pdf.output(dest='S').encode('latin1')
            print(f"FPDF PDF generated successfully, size: {len(pdf_content)} bytes")
            return pdf_content
            
        except Exception as e:
            print(f"Error generating PDF with FPDF: {e}")
            print("Falling back to simple PDF generation")
            return self._generate_simple_pdf_fallback(year, options, session_id)
    
    def _draw_month_fpdf(self, pdf, month_data, month_name, year, x, y, width, height, chinese_font_available=False):
        """Draw a single month using FPDF"""
        try:
            title_height = 5
            weekday_height = 4
            day_height = (height - title_height - weekday_height) / len(month_data['weeks'])
            cell_width = width / 7

            if chinese_font_available:
                pdf.set_font('Chinese', '', 7)
                title = f'{month_name} {year}'
                weekdays = ['日', '一', '二', '三', '四', '五', '六']
            else:
                pdf.set_font('Arial', 'B', 7)
                title = f'{month_name} {year}'
                weekdays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

            pdf.set_xy(x, y)
            pdf.cell(width, title_height, title, 1, 0, 'C')
            pdf.set_xy(x, y + title_height)
            pdf.set_font('Chinese' if chinese_font_available else 'Arial', 'B', 6)
            for weekday in weekdays:
                pdf.cell(cell_width, weekday_height, weekday, 1, 0, 'C')

            pdf.set_font('Chinese' if chinese_font_available else 'Arial', '', 6)
            for week_index, week in enumerate(month_data['weeks']):
                pdf.set_xy(x, y + title_height + weekday_height + week_index * day_height)
                for day_data in week:
                    if day_data is None:
                        pdf.cell(cell_width, day_height, '', 1, 0, 'C')
                    else:
                        day_num = str(day_data['day'])
                        if day_data.get('events'):
                            day_num += '*'
                        pdf.cell(cell_width, day_height, day_num, 1, 0, 'C')
        except Exception as e:
            print(f"Error drawing month {month_name}: {e}")
            # Draw simple fallback
            pdf.set_xy(x, y)
            if chinese_font_available:
                pdf.set_font('Chinese', '', 10)
            else:
                pdf.set_font('Arial', '', 10)
            pdf.cell(width, height, f'{month_name} {year}', 1, 0, 'C')
    
    def _create_month_table_for_pdf(self, month_data, year, month_names, width=None, font_name='Helvetica'):
        """Create a table for a single month in PDF"""
        month = month_data['month']
        
        # Month header
        month_title = f"{month_names[month]} {year}"
        
        # Create table data
        table_data = []
        
        # Add month title row
        table_data.append([month_title, '', '', '', '', '', ''])
        
        # Add weekday headers
        weekdays = ['日', '一', '二', '三', '四', '五', '六']
        table_data.append(weekdays)
        
        # Add calendar days
        for week in month_data['weeks']:
            week_row = []
            for day_data in week:
                if day_data is None:
                    week_row.append('')
                else:
                    day_num = str(day_data['day'])
                    # Add basic event indicators
                    if day_data.get('events'):
                        event_count = len(day_data['events'])
                        if event_count > 0:
                            day_num += f"({event_count})"
                    week_row.append(day_num)
            table_data.append(week_row)
        
        # Keep each month compact enough to fit in a 3-by-4 A4 portrait grid.
        cell_width = (width or 2.7*inch) / 7
        row_heights = [18, 14] + [27] * len(month_data['weeks'])
        table = Table(table_data, colWidths=[cell_width] * 7, rowHeights=row_heights)
        
        # Style the table
        table.setStyle(TableStyle([
            # Month title row
            ('SPAN', (0, 0), (6, 0)),
            ('ALIGN', (0, 0), (6, 0), 'CENTER'),
            ('FONTSIZE', (0, 0), (6, 0), 9),
            ('FONTNAME', (0, 0), (6, 0), font_name),
            ('TOPPADDING', (0, 0), (6, 0), 1),
            ('BOTTOMPADDING', (0, 0), (6, 0), 1),
            
            # Weekday headers
            ('ALIGN', (0, 1), (6, 1), 'CENTER'),
            ('FONTSIZE', (0, 1), (6, 1), 7),
            ('FONTNAME', (0, 1), (6, 1), font_name),
            ('BACKGROUND', (0, 1), (6, 1), colors.lightgrey),
            
            # Calendar days
            ('ALIGN', (0, 2), (6, -1), 'CENTER'),
            ('FONTSIZE', (0, 2), (6, -1), 7),
            ('VALIGN', (0, 2), (6, -1), 'MIDDLE'),
            
            # Grid
            ('GRID', (0, 1), (6, -1), 0.25, colors.black),
            ('BOX', (0, 0), (6, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 1), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 0),
            
            # Weekend styling (Sunday and Saturday)
            ('TEXTCOLOR', (0, 2), (0, -1), colors.red),  # Sunday
            ('TEXTCOLOR', (6, 2), (6, -1), colors.blue), # Saturday
        ]))
        
        return table
    
    def _generate_simple_pdf_fallback(self, year, options, session_id=None):
        """Generate a simple PDF fallback when ReportLab is not available or has issues"""
        try:
            # Create calendar text content first
            calendar_data = self.generate_calendar_data(year, options, session_id)
            
            # Create a properly formatted basic PDF
            pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>
endobj

4 0 obj
<<
/Length 800
>>
stream
BT
/F1 18 Tf
200 750 Td
({year}年年历) Tj
0 -30 Td
/F1 12 Tf
({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 生成) Tj
0 -40 Td
(Sofia年历生成器 - 简化版PDF) Tj
0 -30 Td"""

            # Add month information
            month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                          "七月", "八月", "九月", "十月", "十一月", "十二月"]
            
            y_offset = 0
            for i, month_data in enumerate(calendar_data['months'][:6]):  # First 6 months
                month = month_data['month']
                events_count = sum(len(d.get('events', [])) for week in month_data['weeks'] for d in week if d)
                total_days = len([d for week in month_data['weeks'] for d in week if d])
                
                pdf_content += f"""
0 -{30 + y_offset} Td
({month_names[month]}: {total_days}天, {events_count}个事件) Tj"""
                y_offset += 5

            pdf_content += """
0 -50 Td
(注意: 这是简化版PDF，完整功能需要ReportLab库支持) Tj
0 -20 Td
(如需完整PDF，请安装: pip install reportlab) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000109 00000 n 
0000000252 00000 n 
0000001100 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
1170
%%EOF"""
            
            print(f"Fallback PDF generated, size: {len(pdf_content.encode('utf-8'))} bytes")
            return pdf_content.encode('utf-8')
            
        except Exception as e:
            print(f"Error in PDF fallback: {e}")
            # Return a working minimal PDF
            minimal_pdf = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>
endobj

4 0 obj
<<
/Length 150
>>
stream
BT
/F1 16 Tf
200 700 Td
({year}年年历) Tj
0 -30 Td
/F1 12 Tf
(PDF生成遇到技术问题) Tj
0 -20 Td
(请使用HTML或TXT格式导出) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000109 00000 n 
0000000252 00000 n 
0000000450 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
520
%%EOF"""
            return minimal_pdf.encode('utf-8')
    
    def _generate_calendar_text_content(self, calendar_data, year):
        """Generate text representation of calendar for PDF fallback"""
        content = f"{year}年年历\\n\\n"
        
        month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                      "七月", "八月", "九月", "十月", "十一月", "十二月"]
        
        for month_data in calendar_data['months']:
            month = month_data['month']
            content += f"{month_names[month]}:\\n"
            
            # Add events summary
            events_count = 0
            for week in month_data['weeks']:
                for day_data in week:
                    if day_data and day_data.get('events'):
                        events_count += len(day_data['events'])
            
            content += f"  本月共有{events_count}个事件\\n"
            content += "\\n"
        
        return content
    
    def generate_txt(self, year, options, session_id=None):
        """Generate text calendar"""
        calendar_data = self.generate_calendar_data(year, options, session_id)
        
        txt_content = f"\\n{'='*50}\\n"
        txt_content += f"{' '*20}{year} 年历\\n"
        txt_content += f"{'='*50}\\n\\n"
        
        month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                      "七月", "八月", "九月", "十月", "十一月", "十二月"]
        
        for month_data in calendar_data['months']:
            month = month_data['month']
            txt_content += f"\\n{month_names[month]} {year}\\n"
            txt_content += "-" * 30 + "\\n"
            txt_content += "日  一  二  三  四  五  六\\n"
            
            # Generate text calendar grid with events
            cal_matrix = calendar.monthcalendar(year, month)
            
            # First show the basic calendar layout
            for week in cal_matrix:
                for day in week:
                    if day == 0:
                        txt_content += "   "
                    else:
                        txt_content += f"{day:2d} "
                txt_content += "\\n"
            
            # Then show events for this month
            txt_content += "\\n本月节日事件：\\n"
            has_events = False
            
            for week in month_data['weeks']:
                for day_data in week:
                    if day_data and day_data.get('events'):
                        day = day_data['day']
                        events = day_data['events']
                        
                        for event in events:
                            has_events = True
                            event_name = event['name']
                            event_type = event['type']
                            
                            # Format different event types
                            if event_type == 'personal_holiday':
                                icon = event.get('icon', '🎉')
                                if event.get('is_birthday'):
                                    txt_content += f"  {day:2d}日: {icon} {event_name} (生日)\\n"
                                else:
                                    txt_content += f"  {day:2d}日: {icon} {event_name} (个人节日)\\n"
                            elif event_type == 'festival':
                                txt_content += f"  {day:2d}日: 🎊 {event_name}\\n"
                            elif event_type == 'lunar_festival':
                                txt_content += f"  {day:2d}日: 🏮 {event_name}\\n"
                            elif event_type == 'solar_term':
                                txt_content += f"  {day:2d}日: 🌱 {event_name}\\n"
                            elif event_type == 'auspicious':
                                txt_content += f"  {day:2d}日: 🔮 {event_name}\\n"
                            elif event_type == 'lunar':
                                txt_content += f"  {day:2d}日: 📅 {event_name}\\n"
            
            if not has_events:
                txt_content += "  无特殊节日事件\\n"
            
            txt_content += "\\n"
        
        return txt_content

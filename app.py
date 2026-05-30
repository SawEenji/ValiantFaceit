from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import random
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Конфигурация через переменные окружения
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///valiantfaceit.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV', 'development') == 'production'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ========== МОДЕЛИ БАЗЫ ДАННЫХ ==========
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    valorant_nick = db.Column(db.String(100), nullable=False)
    valorant_tag = db.Column(db.String(10), nullable=False)
    country = db.Column(db.String(50), nullable=False, default='Не указана')
    region = db.Column(db.String(20), nullable=False, default='EU')
    vfp = db.Column(db.Integer, default=0)
    pro_league = db.Column(db.Boolean, default=False)
    subscription = db.Column(db.String(20), default='free')  # free, pro, premium
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default='player')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_daily_reset = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    avatar_frame = db.Column(db.String(100), default='default')
    avatar = db.Column(db.String(200), default='https://i.pravatar.cc/150?img=3')
    bio = db.Column(db.String(500), default='')
    main_agent = db.Column(db.String(50), default='Не выбран')

class UserMission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mission_id = db.Column(db.Integer)
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    loser_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    winner_vfp_change = db.Column(db.Integer, default=0)
    loser_vfp_change = db.Column(db.Integer, default=0)
    screenshot_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='pending')
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Lobby(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    team_size = db.Column(db.Integer, default=5)
    region = db.Column(db.String(20), nullable=False)
    game_mode = db.Column(db.String(50), default='Обычный')
    min_vfp = db.Column(db.Integer, default=0)
    max_vfp = db.Column(db.Integer, default=3000)
    description = db.Column(db.String(200), default='')
    is_full = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LobbyMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobby.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_type = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.String(2000))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AvatarFrame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    price = db.Column(db.Integer)
    css_style = db.Column(db.String(500))
    icon = db.Column(db.String(100), default='🎨')

class UserFrame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    frame_id = db.Column(db.Integer, db.ForeignKey('avatar_frame.id'))
    equipped = db.Column(db.Boolean, default=False)

class CaseDrop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reward_type = db.Column(db.String(50))
    reward_value = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ========== ДАННЫЕ МИССИЙ ==========

MISSIONS = {
    1: {'name': 'Дуэлянт: 25 киллов за матч', 'description': 'Сыграйте за дуэлянта и сделайте 25 убийств в одном матче', 'type': 'duelist', 'vfp_reward': 95, 'target': 25, 'stat': 'kills'},
    2: {'name': 'Дуэлянт: 30 киллов за матч', 'description': 'Сыграйте за дуэлянта и сделайте 30 убийств в одном матче', 'type': 'duelist', 'vfp_reward': 130, 'target': 30, 'stat': 'kills'},
    3: {'name': 'Дуэлянт: 3 MVP за день', 'description': 'Станьте MVP матча 3 раза за день, играя дуэлянта', 'type': 'duelist', 'vfp_reward': 120, 'target': 3, 'stat': 'mvp'},
    4: {'name': 'Дуэлянт: 2 эйса за матч', 'description': 'Сделайте 2 эйса в одном матче, играя дуэлянта', 'type': 'duelist', 'vfp_reward': 150, 'target': 2, 'stat': 'ace'},
    5: {'name': 'Инициатор: 15 ассистов за матч', 'description': 'Сделайте 15 ассистов в одном матче, играя инициатора', 'type': 'initiator', 'vfp_reward': 85, 'target': 15, 'stat': 'assists'},
    6: {'name': 'Инициатор: 20 ассистов за матч', 'description': 'Сделайте 20 ассистов в одном матче, играя инициатора', 'type': 'initiator', 'vfp_reward': 110, 'target': 20, 'stat': 'assists'},
    7: {'name': 'Инициатор: 3 матча подряд с 10+ ассистами', 'description': '3 матча подряд за инициатора с 10+ ассистами', 'type': 'initiator', 'vfp_reward': 100, 'target': 3, 'stat': 'assists_streak'},
    8: {'name': 'Контроллер: 5 постановок спайка', 'description': 'Поставьте спайк 5 раз в одном матче, играя контроллера', 'type': 'controller', 'vfp_reward': 75, 'target': 5, 'stat': 'spike_plants'},
    9: {'name': 'Контроллер: 15 киллов и 5 снятий спайка', 'description': '15 убийств и 5 снятий спайка в одном матче', 'type': 'controller', 'vfp_reward': 105, 'target': 15, 'target2': 5, 'stat': 'kills', 'stat2': 'spike_defuses'},
    10: {'name': 'Страж: 20+ киллов и ≤10 смертей', 'description': '20+ киллов и не более 10 смертей в одном матче', 'type': 'sentinel', 'vfp_reward': 90, 'target': 20, 'target2': 10, 'stat': 'kills', 'stat2': 'deaths'},
    11: {'name': 'Страж: 2 эйса за день', 'description': 'Сделайте 2 эйса за день, играя стража', 'type': 'sentinel', 'vfp_reward': 130, 'target': 2, 'stat': 'ace'},
    12: {'name': '10 ассистов за матч', 'description': 'Сделайте 10 ассистов в одном матче', 'type': 'common', 'vfp_reward': 75, 'target': 10, 'stat': 'assists'},
    13: {'name': '3 MVP за день', 'description': 'Станьте MVP матча 3 раза за день', 'type': 'common', 'vfp_reward': 120, 'target': 3, 'stat': 'mvp'},
    14: {'name': '25 киллов за матч', 'description': 'Сделайте 25 киллов в одном матче', 'type': 'common', 'vfp_reward': 95, 'target': 25, 'stat': 'kills'},
    15: {'name': '35 киллов за матч', 'description': 'Сделайте 35 киллов в одном матче', 'type': 'common', 'vfp_reward': 160, 'target': 35, 'stat': 'kills'},
    16: {'name': '2 эйса за матч', 'description': 'Сделайте 2 эйса в одном матче', 'type': 'common', 'vfp_reward': 140, 'target': 2, 'stat': 'ace'},
    17: {'name': '3 клатча за день', 'description': 'Выиграйте 3 клатча за день (1 против 2+)', 'type': 'common', 'vfp_reward': 125, 'target': 3, 'stat': 'clutch'},
    18: {'name': '5 снятий спайка за матч', 'description': 'Снимите спайк 5 раз в одном матче', 'type': 'common', 'vfp_reward': 80, 'target': 5, 'stat': 'spike_defuses'},
    19: {'name': '8 постановок спайка за день', 'description': 'Поставьте спайк 8 раз за день', 'type': 'common', 'vfp_reward': 70, 'target': 8, 'stat': 'spike_plants'},
    20: {'name': '4 победы подряд', 'description': 'Выиграйте 4 матча подряд', 'type': 'common', 'vfp_reward': 150, 'target': 4, 'stat': 'winstreak'},
}

# Список рамок
AVATAR_FRAMES = [
    {'name': 'DEMON', 'price': 666, 'css_style': 'border: 3px solid #ff4444; box-shadow: 0 0 15px rgba(255,0,0,0.5); border-radius: 50%;', 'icon': '👹'},
    {'name': 'DIAMOND', 'price': 700, 'css_style': 'border: 3px solid #00ffff; box-shadow: 0 0 15px rgba(0,255,255,0.5); border-radius: 50%;', 'icon': '💎'},
    {'name': 'GOLDEN', 'price': 500, 'css_style': 'border: 3px solid #ffd700; box-shadow: 0 0 15px rgba(255,215,0,0.5); border-radius: 50%;', 'icon': '👑'},
    {'name': 'PLATINUM', 'price': 800, 'css_style': 'border: 3px solid #e5e4e2; box-shadow: 0 0 15px rgba(229,228,226,0.5); border-radius: 50%;', 'icon': '⭐'},
    {'name': 'NEBULA', 'price': 1000, 'css_style': 'border: 3px solid #9b59b6; box-shadow: 0 0 20px rgba(155,89,182,0.7); border-radius: 50%; background: linear-gradient(45deg, #667eea, #764ba2);', 'icon': '🌌'},
]

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_level(vfp):
    if vfp >= 1000:
        return 10, "🏆 PRO LEAGUE", "#ffd700"
    elif vfp >= 900:
        return 9, "Мастер", "#c0c0c0"
    elif vfp >= 800:
        return 8, "Элитный", "#cd7f32"
    elif vfp >= 700:
        return 7, "Бриллиант", "#00bfff"
    elif vfp >= 600:
        return 6, "Платина", "#40e0d0"
    elif vfp >= 500:
        return 5, "Золото", "#ffd700"
    elif vfp >= 400:
        return 4, "Серебро", "#c0c0c0"
    elif vfp >= 300:
        return 3, "Бронза", "#cd7f32"
    elif vfp >= 200:
        return 2, "Железо", "#8c8c8c"
    else:
        return 1, "Новичок", "#ffffff"

def update_pro_league(user):
    level, _, _ = get_level(user.vfp)
    if level >= 10 and not user.pro_league:
        user.pro_league = True
        db.session.commit()
        return True
    elif level < 10 and user.pro_league:
        user.pro_league = False
        db.session.commit()
        return True
    return False

def get_online_count():
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    return User.query.filter(User.last_seen > five_min_ago).count()

def open_case(user):
    """Открытие кейса за 150 VFP с шансами из скриншота"""
    if user.vfp < 150:
        return None, "Недостаточно VFP! Нужно 150."
    
    user.vfp -= 150
    rand = random.randint(1, 100)
    
    if rand <= 1:  # 1% - Premium на 1 день
        reward_type = 'premium'
        reward_value = 1
        user.subscription = 'premium'
        message = "🎉 PREMIUM на 1 день! 🎉"
    elif rand <= 6:  # 5% - 200 LP (200 VFP)
        reward_type = 'vfp'
        reward_value = 200
        user.vfp += 200
        message = "+200 VFP"
    elif rand <= 24:  # 18% - 75 LP (75 VFP)
        reward_type = 'vfp'
        reward_value = 75
        user.vfp += 75
        message = "+75 VFP"
    elif rand <= 54:  # 30% - 50 LP (50 VFP)
        reward_type = 'vfp'
        reward_value = 50
        user.vfp += 50
        message = "+50 VFP"
    else:  # 46% - 10 LP (10 VFP)
        reward_type = 'vfp'
        reward_value = 10
        user.vfp += 10
        message = "+10 VFP"
    
    drop = CaseDrop(user_id=user.id, reward_type=reward_type, reward_value=reward_value)
    db.session.add(drop)
    db.session.commit()
    
    return reward_value, message

def get_daily_missions(user):
    """Получить ежедневные миссии для пользователя"""
    today = datetime.utcnow().date()
    last_reset = user.last_daily_reset.date() if user.last_daily_reset else datetime.min.date()
    
    if last_reset != today:
        # Сброс миссий
        UserMission.query.filter_by(user_id=user.id).delete()
        user.last_daily_reset = datetime.utcnow()
        
        # Определяем количество миссий в зависимости от подписки
        if user.subscription == 'premium':
            mission_count = 5  # 3 общие + 2 ролевые
        elif user.subscription == 'pro':
            mission_count = 5  # 3 общие + 2 ролевые
        else:
            mission_count = 3  # 2 общие + 1 ролевая
        
        # Собираем доступные миссии
        agent_roles = ['duelist', 'initiator', 'controller', 'sentinel']
        agent_missions = []
        common_missions = []
        
        for mid, mission in MISSIONS.items():
            if mission['type'] in agent_roles:
                agent_missions.append(mid)
            elif mission['type'] == 'common':
                common_missions.append(mid)
        
        # Выбираем миссии
        selected_missions = []
        
        # Ролевые миссии: для free - 1, для pro/premium - 2
        role_count = 1 if user.subscription == 'free' else 2
        random.shuffle(agent_missions)
        selected_missions.extend(agent_missions[:role_count])
        
        # Общие миссии: для free - 2, для pro/premium - 3
        common_count = 2 if user.subscription == 'free' else 3
        random.shuffle(common_missions)
        selected_missions.extend(common_missions[:common_count])
        
        # Создаём записи миссий
        for mid in selected_missions:
            user_mission = UserMission(user_id=user.id, mission_id=mid, progress=0, completed=False)
            db.session.add(user_mission)
        
        db.session.commit()
    
    # Возвращаем текущие миссии
    user_missions = UserMission.query.filter_by(user_id=user.id).all()
    missions_data = []
    for um in user_missions:
        mission = MISSIONS.get(um.mission_id, {})
        missions_data.append({
            'id': um.mission_id,
            'name': mission.get('name', ''),
            'description': mission.get('description', ''),
            'vfp_reward': mission.get('vfp_reward', 0),
            'progress': um.progress,
            'target': mission.get('target', 1),
            'completed': um.completed
        })
    
    return missions_data

def complete_mission(user, mission_id, progress_increment=1):
    """Завершить миссию (вызывается при отчёте матча)"""
    user_mission = UserMission.query.filter_by(user_id=user.id, mission_id=mission_id, completed=False).first()
    if user_mission:
        mission = MISSIONS.get(mission_id, {})
        user_mission.progress += progress_increment
        if user_mission.progress >= mission.get('target', 1):
            user_mission.completed = True
            user.vfp += mission.get('vfp_reward', 0)
            db.session.commit()
            return True, mission.get('vfp_reward', 0)
    return False, 0

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('⚠️ Для просмотра этой страницы необходимо войти в аккаунт!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ========== СОЗДАНИЕ ТАБЛИЦ ==========

def init_db():
    with app.app_context():
        db.create_all()
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if not User.query.filter_by(username='admin').first():
            if not admin_password:
                admin_password = os.environ.get('GENERATED_ADMIN_PASSWORD') or 'change_me'
            admin = User(
                username='admin',
                password=generate_password_hash(admin_password),
                valorant_nick='Admin',
                valorant_tag='0000',
                country='Россия',
                region='EU',
                vfp=9999,
                is_verified=True,
                role='admin',
                pro_league=True,
                subscription='premium'
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Админ создан")
        
        # Рамки
        for frame_data in AVATAR_FRAMES:
            if not AvatarFrame.query.filter_by(name=frame_data['name']).first():
                frame = AvatarFrame(
                    name=frame_data['name'],
                    price=frame_data['price'],
                    css_style=frame_data['css_style'],
                    icon=frame_data['icon']
                )
                db.session.add(frame)
        db.session.commit()
        
        # Объявление
        if Announcement.query.count() == 0:
            ann = Announcement(
                title='Добро пожаловать в ValiantFaceit!',
                content='Открывайте Valiant Case, покупайте рамки, выполняйте миссии и повышайте свой уровень!',
                created_by=1
            )
            db.session.add(ann)
            db.session.commit()

# ========== HTML ШАБЛОН (сокращён из-за размера, основные страницы) ==========

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>ValiantFaceit - Valorant Mobile Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            padding: 16px;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
            background: rgba(255,255,255,0.95);
            border-radius: 24px;
            padding: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .navbar {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
        }
        .navbar a {
            text-decoration: none;
            color: #5b47fb;
            font-weight: 600;
            font-size: 12px;
            padding: 5px 8px;
        }
        h1 { font-size: 1.6rem; margin-bottom: 15px; color: #1a1a2e; }
        h2 { font-size: 1.2rem; margin: 20px 0 10px; color: #1a1a2e; }
        .flash {
            padding: 12px;
            margin: 10px 0;
            border-radius: 12px;
            font-size: 14px;
        }
        .flash.success { background: #d4edda; color: #155724; border-left: 4px solid #28a745; }
        .flash.error { background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
        .flash.warning { background: #fff3cd; color: #856404; border-left: 4px solid #ffc107; }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; font-weight: 600; color: #333; }
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 12px;
            font-size: 14px;
        }
        button {
            background: linear-gradient(135deg, #5b47fb, #7c3aed);
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            width: 100%;
            cursor: pointer;
        }
        .card {
            background: #f8f9ff;
            padding: 16px;
            margin: 15px 0;
            border-radius: 16px;
            border-left: 4px solid #5b47fb;
        }
        .case-card {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: white;
            text-align: center;
        }
        .case-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin: 15px 0;
        }
        .case-stat {
            background: rgba(255,255,255,0.1);
            padding: 8px;
            border-radius: 10px;
        }
        .shop-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            margin: 10px 0;
            background: #f0f0f0;
            border-radius: 12px;
        }
        .frame-preview {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: #5b47fb;
            display: inline-block;
        }
        .mission-item {
            background: #f0f0f0;
            padding: 12px;
            margin: 10px 0;
            border-radius: 12px;
        }
        .mission-progress {
            background: #ddd;
            border-radius: 10px;
            height: 8px;
            margin-top: 8px;
        }
        .mission-progress-bar {
            background: #5b47fb;
            height: 8px;
            border-radius: 10px;
            width: 0%;
        }
        .subscription-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: bold;
        }
        .premium { background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000; }
        .pro { background: linear-gradient(135deg, #c0c0c0, #808080); color: #000; }
        .free { background: #666; color: white; }
        .stats-card {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 16px;
            margin: 15px 0;
            border-radius: 16px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        .stat-item {
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-number { font-size: 24px; font-weight: bold; }
        @media (max-width: 600px) {
            .container { padding: 16px; }
            .navbar a { font-size: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="navbar">
            <a href="/">🏠 Главная</a>
            <a href="/leaderboard">🏆 Рейтинг</a>
            <a href="/missions">📋 Миссии</a>
            <a href="/case">🎲 Valiant Case</a>
            <a href="/shop">🛍️ Магазин</a>
            {% if session.user_id %}
                <a href="/dashboard">👤 Профиль</a>
                <a href="/lobbies">🎮 Лобби</a>
                <a href="/logout">🚪 Выход</a>
            {% else %}
                <a href="/login">🔐 Вход</a>
                <a href="/register">📝 Регистрация</a>
            {% endif %}
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="stats-card">
            <div class="stats-grid">
                <div class="stat-item"><div class="stat-number">{{ total_users }}</div><div>Всего игроков</div></div>
                <div class="stat-item"><div class="stat-number">{{ online_count }}</div><div>Онлайн</div></div>
                <div class="stat-item"><div class="stat-number">{{ total_matches }}</div><div>Матчей</div></div>
                <div class="stat-item"><div class="stat-number">{{ pro_count }}</div><div>PRO League</div></div>
            </div>
        </div>
        
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

# ========== СТРАНИЦЫ ==========

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
            <h1>🎮 ValiantFaceit</h1>
            <p>Платформа для поиска тиммейтов в Valorant Mobile</p>
            <div class="card"><h3>⚡ Что вас ждёт:</h3>
            <ul><li>Valiant Case с редкими наградами</li><li>Уникальные рамки профиля</li><li>20+ ежедневных миссий</li><li>PRO League для лучших</li></ul></div>
            <div style="display:flex;gap:12px;margin-top:20px">
                <a href="/register" style="flex:1"><button>Регистрация</button></a>
                <a href="/login" style="flex:1"><button style="background:#4a3b8c">Вход</button></a>
            </div>
        '''), total_users=User.query.count(), online_count=get_online_count(),
           total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())
    
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    content = '<h1>🎮 ValiantFaceit</h1>'
    for ann in announcements:
        content += f'<div class="card"><h3>📢 {ann.title}</h3><p>{ann.content}</p></div>'
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        valorant_nick = request.form['valorant_nick']
        valorant_tag = request.form['valorant_tag']
        country = request.form['country']
        region = request.form['region']
        
        if User.query.filter_by(username=username).first():
            flash('Логин занят!', 'error')
            return redirect(url_for('register'))
        
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            valorant_nick=valorant_nick,
            valorant_tag=valorant_tag,
            country=country,
            region=region,
            vfp=0,
            is_verified=False
        )
        db.session.add(new_user)
        db.session.commit()
        flash('✅ Регистрация успешна! Ожидайте проверки.', 'success')
        return redirect(url_for('login'))
    
    countries = ['Россия', 'Украина', 'Беларусь', 'Казахстан', 'Германия', 'Франция', 'Другая']
    regions = ['EU', 'NA', 'ASIA', 'RU']
    content = '<h1>Регистрация</h1><form method="POST">'
    content += '<div class="form-group"><label>Логин:</label><input type="text" name="username" required></div>'
    content += '<div class="form-group"><label>Пароль:</label><input type="password" name="password" required></div>'
    content += '<div class="form-group"><label>Ник в Valorant:</label><input type="text" name="valorant_nick" required></div>'
    content += '<div class="form-group"><label>Тег:</label><input type="text" name="valorant_tag" placeholder="1234" required></div>'
    content += '<div class="form-group"><label>Страна:</label><select name="country">' + ''.join(f'<option>{c}</option>' for c in countries) + '</select></div>'
    content += '<div class="form-group"><label>Регион:</label><select name="region">' + ''.join(f'<option>{r}</option>' for r in regions) + '</select></div>'
    content += '<button type="submit">Зарегистрироваться</button></form>'
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            user.last_seen = datetime.utcnow()
            db.session.commit()
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('index'))
        flash('Неверный логин или пароль!', 'error')
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '<h1>Вход</h1><form method="POST"><div class="form-group"><label>Логин:</label><input type="text" name="username" required></div><div class="form-group"><label>Пароль:</label><input type="password" name="password" required></div><button type="submit">Войти</button></form>'),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    level, level_name, level_color = get_level(user.vfp)
    user_frame = None
    if user.avatar_frame != 'default':
        frame = AvatarFrame.query.filter_by(name=user.avatar_frame).first()
        if frame:
            user_frame = frame
    
    content = f'''
        <h1>👤 {user.username}</h1>
        <div class="card" style="text-align:center">
            <div style="width:100px;height:100px;border-radius:50%;margin:0 auto 10px;background:#5b47fb;display:flex;align-items:center;justify-content:center;font-size:40px" {'style="'+frame.css_style+'"' if user_frame else ''}>
                {user.username[0].upper()}
            </div>
            <p><strong>🎮</strong> {user.valorant_nick}#{user.valorant_tag}</p>
            <p><strong>🌍</strong> {user.country} | <strong>🌐</strong> {user.region}</p>
            <p><strong>🏆 VFP:</strong> {user.vfp}</p>
            <p><strong>⭐ Уровень:</strong> <span style="background:{level_color};padding:4px 12px;border-radius:20px">{level} LVL - {level_name}</span></p>
            <p><strong>👑 PRO League:</strong> {'✅ Да' if user.pro_league else '❌ Нет'}</p>
            <p><strong>📦 Подписка:</strong> <span class="subscription-badge {user.subscription}">{user.subscription.upper()}</span></p>
            <p><strong>📊 Статистика:</strong> {user.wins} побед / {user.losses} поражений</p>
        </div>
    '''
    if user.role in ['moderator', 'admin']:
        content += '<a href="/admin_panel"><button style="background:#6c5ce7">🛡️ Админ панель</button></a>'
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/missions')
@login_required
def missions():
    user = User.query.get(session['user_id'])
    daily_missions = get_daily_missions(user)
    
    content = f'''
        <h1>📋 Ежедневные миссии</h1>
        <div class="card">
            <p><strong>📦 Ваша подписка:</strong> <span class="subscription-badge {user.subscription}">{user.subscription.upper()}</span></p>
            <p>Миссий сегодня: {len(daily_missions)}</p>
        </div>
    '''
    
    for mission in daily_missions:
        percent = (mission['progress'] / mission['target']) * 100 if mission['target'] > 0 else 0
        status = '✅' if mission['completed'] else '⏳'
        content += f'''
            <div class="mission-item">
                <div style="display:flex;justify-content:space-between">
                    <strong>{status} {mission['name']}</strong>
                    <span>+{mission['vfp_reward']} VFP</span>
                </div>
                <p style="font-size:12px;color:#666">{mission['description']}</p>
                <div class="mission-progress">
                    <div class="mission-progress-bar" style="width:{percent}%"></div>
                </div>
                <p style="font-size:11px;margin-top:5px">Прогресс: {mission['progress']}/{mission['target']}</p>
            </div>
        '''
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/case')
@login_required
def case():
    user = User.query.get(session['user_id'])
    content = f'''
        <h1>🎲 Valiant Case</h1>
        <div class="card case-card">
            <h2>LUMO REWARD DROP</h2>
            <p>Кейс за 150 VFP. Внутри награды и редкий шанс на Premium!</p>
            <div class="case-stats">
                <div class="case-stat">🎟️ PREMIUM 1 день<br>Шанс: 1%</div>
                <div class="case-stat">💰 +200 VFP<br>Шанс: 5%</div>
                <div class="case-stat">💰 +75 VFP<br>Шанс: 18%</div>
                <div class="case-stat">💰 +50 VFP<br>Шанс: 30%</div>
                <div class="case-stat">💰 +10 VFP<br>Шанс: 46%</div>
            </div>
            <p>Ваш баланс: {user.vfp} VFP</p>
            <form method="POST" action="/open_case">
                <button type="submit" {'disabled' if user.vfp < 150 else ''}>🎁 ОТКРЫТЬ КЕЙС (150 VFP)</button>
            </form>
        </div>
    '''
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/open_case', methods=['POST'])
@login_required
def open_case():
    user = User.query.get(session['user_id'])
    reward, message = open_case(user)
    if reward is None:
        flash(message, 'error')
    else:
        flash(f'🎉 Вы открыли кейс и получили: {message}!', 'success')
    return redirect(url_for('case'))

@app.route('/shop')
@login_required
def shop():
    user = User.query.get(session['user_id'])
    frames = AvatarFrame.query.all()
    owned_frames = [uf.frame_id for uf in UserFrame.query.filter_by(user_id=user.id).all()]
    
    content = '<h1>🛍️ Магазин рамок</h1><div class="card">'
    for frame in frames:
        owned = frame.id in owned_frames
        equipped = user.avatar_frame == frame.name
        content += f'''
            <div class="shop-item">
                <div>
                    <span style="font-size:24px">{frame.icon}</span>
                    <strong>{frame.name}</strong>
                    <div style="width:40px;height:40px;border-radius:50%;background:#5b47fb;display:inline-block;margin-left:10px" style="{frame.css_style}"></div>
                </div>
                <div>
                    <span style="color:#5b47fb;font-weight:bold">{frame.price} VFP</span>
                    {'<span style="color:green">✅ Куплена</span>' if owned else '<a href="/buy_frame/'+str(frame.id)+'"><button style="width:auto;padding:6px12px">Купить</button></a>'}
                    {'<a href="/equip_frame/'+str(frame.id)+'"><button style="width:auto;padding:6px12px;background:#28a745">Надеть</button></a>' if owned and not equipped else ''}
                    {'<span style="color:green">✨ Надета</span>' if equipped else ''}
                </div>
            </div>
        '''
    content += '</div>'
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/buy_frame/<int:frame_id>')
@login_required
def buy_frame(frame_id):
    user = User.query.get(session['user_id'])
    frame = AvatarFrame.query.get(frame_id)
    if not frame:
        flash('Рамка не найдена!', 'error')
        return redirect(url_for('shop'))
    
    if UserFrame.query.filter_by(user_id=user.id, frame_id=frame_id).first():
        flash('У вас уже есть эта рамка!', 'warning')
        return redirect(url_for('shop'))
    
    if user.vfp < frame.price:
        flash(f'Недостаточно VFP! Нужно {frame.price}', 'error')
        return redirect(url_for('shop'))
    
    user.vfp -= frame.price
    user_frame = UserFrame(user_id=user.id, frame_id=frame_id)
    db.session.add(user_frame)
    db.session.commit()
    flash(f'✅ Вы купили рамку {frame.name}!', 'success')
    return redirect(url_for('shop'))

@app.route('/equip_frame/<int:frame_id>')
@login_required
def equip_frame(frame_id):
    user = User.query.get(session['user_id'])
    frame = AvatarFrame.query.get(frame_id)
    if not frame:
        flash('Рамка не найдена!', 'error')
        return redirect(url_for('shop'))
    
    user_frame = UserFrame.query.filter_by(user_id=user.id, frame_id=frame_id).first()
    if not user_frame:
        flash('У вас нет этой рамки!', 'error')
        return redirect(url_for('shop'))
    
    user.avatar_frame = frame.name
    db.session.commit()
    flash(f'✅ Вы надели рамку {frame.name}!', 'success')
    return redirect(url_for('shop'))

@app.route('/leaderboard')
@login_required
def leaderboard():
    players = User.query.filter_by(is_verified=True).order_by(User.vfp.desc()).limit(50).all()
    content = '<h1>🏆 Таблица лидеров</h1><table style="width:100%"><tr><th>#</th><th>Игрок</th><th>VFP</th><th>Уровень</th></tr>'
    for i, p in enumerate(players, 1):
        level, _, _ = get_level(p.vfp)
        content += f'<tr><td>{i}</td><td>{p.username}</td><td>{p.vfp}</td><td>{level} LVL</td></tr>'
    content += '</table>'
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/lobbies')
@login_required
def lobbies():
    user = User.query.get(session['user_id'])
    other_lobbies = Lobby.query.filter(Lobby.creator_id != user.id, Lobby.is_full == False).all()
    content = '<h1>🎮 Лобби</h1><div class="card"><h2>Создать лобби</h2><form method="POST" action="/create_lobby">'
    content += '<div class="form-group"><label>Размер:</label><select name="team_size"><option value="5">5x5</option><option value="4">4x4</option><option value="3">3x3</option></select></div>'
    content += '<div class="form-group"><label>Регион:</label><select name="region"><option>EU</option><option>NA</option><option>ASIA</option><option>RU</option></select></div>'
    content += '<div class="form-group"><label>Min VFP:</label><input type="number" name="min_vfp" value="0"></div>'
    content += '<div class="form-group"><label>Max VFP:</label><input type="number" name="max_vfp" value="3000"></div>'
    content += '<div class="form-group"><label>Описание:</label><textarea name="description"></textarea></div>'
    content += '<button type="submit">Создать</button></form></div>'
    for lobby in other_lobbies:
        creator = User.query.get(lobby.creator_id)
        content += f'<div class="card"><p><strong>{creator.username}</strong> | {lobby.region} | {lobby.team_size}x{lobby.team_size}</p><p>{lobby.description}</p><a href="/join_lobby/{lobby.id}"><button>Вступить</button></a></div>'
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/create_lobby', methods=['POST'])
@login_required
def create_lobby():
    user = User.query.get(session['user_id'])
    if not user.is_verified:
        flash('Только подтверждённые игроки!', 'error')
        return redirect(url_for('lobbies'))
    lobby = Lobby(
        creator_id=user.id,
        team_size=int(request.form['team_size']),
        region=request.form['region'],
        min_vfp=int(request.form['min_vfp']),
        max_vfp=int(request.form['max_vfp']),
        description=request.form.get('description', '')
    )
    db.session.add(lobby)
    db.session.commit()
    db.session.add(LobbyMember(lobby_id=lobby.id, user_id=user.id))
    db.session.commit()
    flash('Лобби создано!', 'success')
    return redirect(url_for('lobbies'))

@app.route('/join_lobby/<int:lobby_id>')
@login_required
def join_lobby(lobby_id):
    user = User.query.get(session['user_id'])
    lobby = Lobby.query.get(lobby_id)
    if not user.is_verified:
        flash('Только подтверждённые игроки!', 'error')
        return redirect(url_for('lobbies'))
    if LobbyMember.query.filter_by(lobby_id=lobby_id, user_id=user.id).first():
        flash('Вы уже в лобби!', 'warning')
        return redirect(url_for('lobbies'))
    if LobbyMember.query.filter_by(lobby_id=lobby_id).count() >= lobby.team_size:
        flash('Лобби полно!', 'error')
        return redirect(url_for('lobbies'))
    db.session.add(LobbyMember(lobby_id=lobby_id, user_id=user.id))
    db.session.commit()
    flash('Вы вступили!', 'success')
    return redirect(url_for('lobbies'))

@app.route('/admin_panel')
@login_required
def admin_panel():
    user = User.query.get(session['user_id'])
    if user.role not in ['moderator', 'admin']:
        flash('Доступ запрещён!', 'error')
        return redirect(url_for('dashboard'))
    
    pending_users = User.query.filter_by(is_verified=False, role='player').all()
    pending_matches = Match.query.filter_by(status='pending').all()
    
    content = '<h1>🛡️ Админ панель</h1>'
    content += '<div class="card"><h2>Неподтверждённые игроки</h2>'
    for p in pending_users:
        content += f'<p>{p.username} | {p.valorant_nick}#{p.valorant_tag} <a href="/verify_user/{p.id}"><button style="width:auto">✅</button></a> <a href="/delete_user/{p.id}"><button style="width:auto">❌</button></a></p>'
    content += '</div><div class="card"><h2>Матчи на проверке</h2>'
    for m in pending_matches:
        winner = User.query.get(m.winner_id)
        loser = User.query.get(m.loser_id)
        content += f'<p>{winner.username if winner else "?"} vs {loser.username if loser else "?"} <a href="/approve_match/{m.id}"><button style="width:auto">✅</button></a> <a href="/reject_match/{m.id}"><button style="width:auto">❌</button></a></p>'
    content += '</div><div class="card"><h2>Редактировать игрока</h2><form method="POST" action="/edit_player"><input type="text" name="username" placeholder="Логин"><input type="number" name="vfp" placeholder="VFP"><select name="subscription"><option value="free">Free</option><option value="pro">Pro</option><option value="premium">Premium</option></select><button type="submit">Изменить</button></form></div>'
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
                                  total_users=User.query.count(), online_count=get_online_count(),
                                  total_matches=Match.query.filter_by(status='approved').count(), pro_count=User.query.filter_by(pro_league=True).count())

@app.route('/verify_user/<int:user_id>')
@login_required
def verify_user(user_id):
    admin = User.query.get(session['user_id'])
    if admin.role not in ['moderator', 'admin']:
        flash('Доступ запрещён!', 'error')
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user:
        user.is_verified = True
        db.session.commit()
        flash(f'Игрок {user.username} подтверждён!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/approve_match/<int:match_id>')
@login_required
def approve_match(match_id):
    admin = User.query.get(session['user_id'])
    if admin.role not in ['moderator', 'admin']:
        flash('Доступ запрещён!', 'error')
        return redirect(url_for('dashboard'))
    match = Match.query.get(match_id)
    if match and match.status == 'pending':
        winner = User.query.get(match.winner_id)
        loser = User.query.get(match.loser_id)
        if winner:
            winner.vfp += match.winner_vfp_change
            winner.wins += 1
            update_pro_league(winner)
        if loser:
            loser.vfp += match.loser_vfp_change
            if loser.vfp < 0:
                loser.vfp = 0
            loser.losses += 1
            update_pro_league(loser)
        match.status = 'approved'
        db.session.commit()
        flash('Матч подтверждён!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/reject_match/<int:match_id>')
@login_required
def reject_match(match_id):
    admin = User.query.get(session['user_id'])
    if admin.role not in ['moderator', 'admin']:
        flash('Доступ запрещён!', 'error')
        return redirect(url_for('dashboard'))
    match = Match.query.get(match_id)
    if match:
        match.status = 'rejected'
        db.session.commit()
        flash('Матч отклонён', 'warning')
    return redirect(url_for('admin_panel'))

@app.route('/edit_player', methods=['POST'])
@login_required
def edit_player():
    admin = User.query.get(session['user_id'])
    if admin.role not in ['moderator', 'admin']:
        flash('Доступ запрещён!', 'error')
        return redirect(url_for('dashboard'))
    username = request.form['username']
    player = User.query.filter_by(username=username).first()
    if player:
        if request.form.get('vfp'):
            player.vfp = int(request.form['vfp'])
            update_pro_league(player)
        if request.form.get('subscription'):
            player.subscription = request.form['subscription']
        db.session.commit()
        flash(f'Данные {player.username} обновлены!', 'success')
    else:
        flash('Игрок не найден!', 'error')
    return redirect(url_for('admin_panel'))

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    admin = User.query.get(session['user_id'])
    if admin.role not in ['moderator', 'admin']:
        flash('Доступ запрещён!', 'error')
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user and user.id != admin.id:
        db.session.delete(user)
        db.session.commit()
        flash(f'Пользователь удалён!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    debug = os.environ.get('FLASK_ENV','development') != 'production'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=debug)

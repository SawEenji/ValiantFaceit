import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'development'

from app import app, db


def setup_function():
    with app.app_context():
        db.create_all()


def teardown_function():
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_health():
    client = app.test_client()
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json().get('status') == 'ok'


def test_register_and_login():
    client = app.test_client()
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'testpass',
        'valorant_nick': 'TestNick',
        'valorant_tag': '1234',
        'country': 'Россия',
        'region': 'EU'
    }, follow_redirects=True)
    assert '✅ Регистрация успешна' in response.get_data(as_text=True)

    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    }, follow_redirects=True)
    assert 'Добро пожаловать' in response.get_data(as_text=True)

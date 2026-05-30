import requests


def test_health():
    resp = requests.get('http://127.0.0.1:5000/health')
    assert resp.status_code == 200
    assert resp.json().get('status') == 'ok'

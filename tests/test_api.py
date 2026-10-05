from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_geo_resolve():
    r = client.get("/v1/tools/geo_resolve?city=Mysuru")
    assert r.status_code == 200
    assert r.json()["city"] == "Mysuru"

def test_tools():
    r = client.get("/v1/tools")
    assert r.status_code == 200
    assert len(r.json()["tools"]) == 8

def test_chat():
    r = client.post("/v1/chat", json={"message":"Will it rain tomorrow?","city":"Mysuru","language":"en"})
    assert r.status_code == 200
    assert r.json()["answer"]

def test_advisory():
    r = client.post("/v1/advisory", json={"sector":"agriculture","city":"Mysuru","latitude":12.29,"longitude":76.63})
    assert r.status_code == 200
    assert len(r.json()["calendar"]) == 7

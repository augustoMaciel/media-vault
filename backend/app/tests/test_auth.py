"""Auth endpoint tests: registration, login, and /me session check."""


def test_register_success_returns_201_and_token(client):
    resp = client.post("/auth/register",
                       json={"email": "Alice@Example.com", "password": "StrongPass1!"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert "access_token" in body
    # Email is normalized to lowercase.
    assert body["user"]["email"] == "alice@example.com"
    assert "password_hash" not in body["user"]


def test_register_duplicate_email_returns_409(client):
    payload = {"email": "dup@example.com", "password": "StrongPass1!"}
    assert client.post("/auth/register", json=payload).status_code == 201
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 409


def test_register_invalid_email_returns_400(client):
    resp = client.post("/auth/register",
                       json={"email": "not-an-email", "password": "StrongPass1!"})
    assert resp.status_code == 400


def test_register_weak_password_returns_400(client):
    # Too short, no upper/digit/symbol.
    resp = client.post("/auth/register",
                       json={"email": "weak@example.com", "password": "abcdef"})
    assert resp.status_code == 400
    assert "messages" in resp.get_json()


def test_register_strong_password_returns_201(client):
    resp = client.post("/auth/register",
                       json={"email": "strong@example.com", "password": "Str0ng&Pass99"})
    assert resp.status_code == 201


def test_login_success_returns_token(client):
    client.post("/auth/register",
                json={"email": "log@example.com", "password": "StrongPass1!"})
    resp = client.post("/auth/login",
                       json={"email": "log@example.com", "password": "StrongPass1!"})
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_wrong_password_returns_401_generic(client):
    client.post("/auth/register",
                json={"email": "wp@example.com", "password": "StrongPass1!"})
    resp = client.post("/auth/login",
                       json={"email": "wp@example.com", "password": "WrongPass1!"})
    assert resp.status_code == 401
    # Generic message — must not reveal which field was wrong.
    assert resp.get_json()["message"] == "Invalid email or password."


def test_login_unknown_email_returns_401_generic(client):
    resp = client.post("/auth/login",
                       json={"email": "ghost@example.com", "password": "StrongPass1!"})
    assert resp.status_code == 401
    assert resp.get_json()["message"] == "Invalid email or password."


def test_me_without_token_returns_401(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_token_returns_user_without_hash(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert "email" in body
    assert "password_hash" not in body

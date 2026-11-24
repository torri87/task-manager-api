from datetime import UTC, datetime, timedelta


def future(days=7):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()



def make_user(client, email="user@example.com"):
    reg = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert reg.status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": "password123"})
    token = login.json()["access_token"]
    return reg.json()["id"], {"Authorization": f"Bearer {token}"}


def create_task(client, headers, **fields):
    payload = {"title": "Test task", "priority": "Medium", "deadline": future()}
    payload.update(fields)
    response = client.post("/tasks", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def change_status(client, headers, task_id, new_status):
    return client.patch(
        f"/tasks/{task_id}/status", json={"status": new_status}, headers=headers
    )


def test_register_login_and_me(client):
    user_id, headers = make_user(client)
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_tasks_require_token(client):
    response = client.get("/tasks")
    assert response.status_code == 401


def test_create_task(client):
    user_id, headers = make_user(client)
    task = create_task(client, headers, title="Написати звіт", priority="High")
    assert task["title"] == "Написати звіт"
    assert task["status"] == "Backlog"
    assert task["author_id"] == user_id


def test_deadline_in_past_is_rejected(client):
    _, headers = make_user(client)
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    response = client.post(
        "/tasks", json={"title": "Стара", "deadline": past}, headers=headers
    )
    assert response.status_code == 422


def test_cannot_delete_task_in_progress(client):
    _, headers = make_user(client)
    task = create_task(client, headers)
    change_status(client, headers, task["id"], "In Progress")

    response = client.delete(f"/tasks/{task['id']}", headers=headers)
    assert response.status_code == 409

    change_status(client, headers, task["id"], "Cancelled")
    response = client.delete(f"/tasks/{task['id']}", headers=headers)
    assert response.status_code == 204


def test_create_and_list_comments(client):
    user_id, headers = make_user(client)
    task = create_task(client, headers)
    url = f"/tasks/{task['id']}/comments"

    response = client.post(url, json={"content": "Перший"}, headers=headers)
    assert response.status_code == 201
    assert response.json()["author_id"] == user_id
    client.post(url, json={"content": "Другий"}, headers=headers)

    response = client.get(url, headers=headers)
    assert [c["content"] for c in response.json()] == ["Перший", "Другий"]
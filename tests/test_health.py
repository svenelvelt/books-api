def test_liveness_returns_ok(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_ok_when_database_is_reachable(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

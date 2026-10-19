def assert_error(response, status_code: int, code: str) -> dict:
    assert response.status_code == status_code
    body = response.json()
    assert body["code"] == code
    assert isinstance(body["detail"], str)
    return body

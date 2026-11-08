"""种子数据开关测试：演示账号默认不创建。"""


def test_demo_user_is_not_seeded_by_default(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "demo@meditour.com", "password": "Demo123456"},
    )
    assert response.status_code == 401

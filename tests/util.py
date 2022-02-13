def login(client, email, password):
    return client.post(
        "/auth/login",
        data=dict(email=email, password=password),
        follow_redirects=True,
    )


def logout(client):
    return client.get(
        "/auth/logout",
        follow_redirects=True,
    )

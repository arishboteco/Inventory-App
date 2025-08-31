def test_item_pagination(client, item_factory):
    for i in range(11):
        item_factory(name=f"Item {i}")
    response = client.get("/api/items/?page=2&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 11
    assert len(data["results"]) == 5


def test_item_filtering(client, item_factory):
    item_factory(name="Sugar")
    item_factory(name="Salt")
    response = client.get("/api/items/?name__icontains=sug")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["results"][0]["name"] == "Sugar"

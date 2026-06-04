"""
Integration tests for the events endpoints — use the in-memory DB fixture.
"""


# ----- helpers -----

VALID_EVENT_PAYLOAD = {
    "name": "Manchester City vs Liverpool",
    "sport": "football",
    "start_time": "2026-06-15T15:00:00+01:00",
    "venue": "Etihad Stadium",
}


def _create_event(client, **overrides):
    payload = {**VALID_EVENT_PAYLOAD, **overrides}
    response = client.post("/events/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ----- smoke -----

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


# ----- POST /events -----

class TestCreateEvent:
    def test_happy_path(self, client):
        body = _create_event(client)
        assert body["name"] == "Manchester City vs Liverpool"
        assert body["status"] == "scheduled"
        assert body["id"] >= 1

    def test_naive_datetime_rejected(self, client):
        payload = {**VALID_EVENT_PAYLOAD, "start_time": "2026-06-15T15:00:00"}
        response = client.post("/events/", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "validation_error"
        assert any(
            "timezone" in detail.get("msg", "").lower()
            for detail in body["error"]["details"]
        )

    def test_start_time_normalised_to_utc(self, client):
        body = _create_event(client)
        # 15:00 +01:00 -> 14:00 UTC. Response carries the offset.
        assert "14:00:00" in body["start_time"]


# ----- GET /events/{id} and list -----

class TestReadEvents:
    def test_get_by_id(self, client):
        created = _create_event(client)
        response = client.get(f"/events/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_404(self, client):
        response = client.get("/events/9999")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_list_filters_by_sport(self, client):
        _create_event(client, sport="football", name="Football match")
        _create_event(client, sport="basketball", name="Basketball match")
        response = client.get("/events/?sport=basketball")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["name"] == "Basketball match"


# ----- PATCH status -----

class TestPatchStatus:
    def test_valid_transition(self, client):
        created = _create_event(client)
        response = client.patch(
            f"/events/{created['id']}/status",
            json={"status": "live"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "live"

    def test_invalid_transition_returns_409(self, client):
        created = _create_event(client)
        # scheduled -> completed is invalid (must go through live)
        response = client.patch(
            f"/events/{created['id']}/status",
            json={"status": "completed"},
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"]["code"] == "conflict"
        assert "scheduled" in body["error"]["message"]

    def test_terminal_state_rejects_any_transition(self, client):
        created = _create_event(client)
        client.patch(f"/events/{created['id']}/status", json={"status": "live"})
        client.patch(f"/events/{created['id']}/status", json={"status": "completed"})
        # now terminal
        response = client.patch(
            f"/events/{created['id']}/status",
            json={"status": "live"},
        )
        assert response.status_code == 409


# ----- POST result -----

class TestRecordResult:
    def _complete_event(self, client):
        created = _create_event(client)
        client.patch(f"/events/{created['id']}/status", json={"status": "live"})
        client.patch(f"/events/{created['id']}/status", json={"status": "completed"})
        return created["id"]

    def test_happy_path(self, client):
        event_id = self._complete_event(client)
        response = client.post(
            f"/events/{event_id}/result",
            json={"home_score": 2, "away_score": 1, "winner": "home"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["event_id"] == event_id
        assert body["home_score"] == 2

    def test_event_not_completed_returns_409(self, client):
        created = _create_event(client)  # status=scheduled
        response = client.post(
            f"/events/{created['id']}/result",
            json={"home_score": 1, "away_score": 0, "winner": "home"},
        )
        assert response.status_code == 409

    def test_duplicate_result_returns_409(self, client):
        event_id = self._complete_event(client)
        client.post(
            f"/events/{event_id}/result",
            json={"home_score": 2, "away_score": 1, "winner": "home"},
        )
        # second one fails — Decision 2
        response = client.post(
            f"/events/{event_id}/result",
            json={"home_score": 3, "away_score": 3, "winner": "draw"},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    def test_winner_inconsistent_with_scores_returns_422(self, client):
        event_id = self._complete_event(client)
        response = client.post(
            f"/events/{event_id}/result",
            json={"home_score": 3, "away_score": 1, "winner": "away"},
        )
        assert response.status_code == 422
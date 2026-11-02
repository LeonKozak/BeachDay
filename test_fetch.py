import pytest
import requests

import fetch

URL = "https://example.com"
PARAMS = {"latitude": 38.37}
GOOD_JSON = {"hourly": "some data"}

TIMEOUT = requests.exceptions.Timeout("too slow")
LOST_CONNECTION = requests.exceptions.ConnectionError("no connection")


class FakeResponse:
    """Stands in for a real response, with only the parts request_json uses."""

    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self.json_data = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"status {self.status_code}", response=self
            )

    def json(self):
        return self.json_data


SERVER_ERROR = FakeResponse(503)
NOT_FOUND = FakeResponse(404)
SUCCESS = FakeResponse(200, GOOD_JSON)


@pytest.fixture
def fake_request(monkeypatch):
    """Replace requests.get and time.sleep, so tests use no network and don't wait.

    A test calls fake_request with what each attempt should do in turn: an error
    to raise or a response to return. It gets back the record of what happened.
    """

    class Record:
        attempts = 0
        waits = []

    def set_outcomes(*outcomes):
        Record.attempts = 0
        Record.waits = []

        def fake_get(url, params, timeout):
            outcome = outcomes[Record.attempts]
            Record.attempts += 1
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr(fetch.requests, "get", fake_get)
        monkeypatch.setattr(fetch.time, "sleep", Record.waits.append)
        return Record

    return set_outcomes


@pytest.mark.parametrize("failure", [TIMEOUT, LOST_CONNECTION, SERVER_ERROR])
def test_fails_twice_then_succeeds(fake_request, failure):
    record = fake_request(failure, failure, SUCCESS)

    assert fetch.request_json_with_retries(URL, PARAMS) == GOOD_JSON
    assert record.attempts == 3
    assert record.waits == [1, 2]


def test_success_first_time_does_not_wait(fake_request):
    record = fake_request(SUCCESS)

    assert fetch.request_json_with_retries(URL, PARAMS) == GOOD_JSON
    assert record.attempts == 1
    assert record.waits == []


def test_succeeds_on_the_very_last_try(fake_request):
    record = fake_request(TIMEOUT, TIMEOUT, TIMEOUT, SUCCESS)

    assert fetch.request_json_with_retries(URL, PARAMS) == GOOD_JSON
    assert record.attempts == 4
    assert record.waits == [1, 2, 4]


@pytest.mark.parametrize(
    "failure, error_type",
    [
        (TIMEOUT, requests.exceptions.Timeout),
        (LOST_CONNECTION, requests.exceptions.ConnectionError),
        (SERVER_ERROR, requests.exceptions.HTTPError),
    ],
)
def test_gives_up_after_three_retries(fake_request, failure, error_type):
    record = fake_request(failure, failure, failure, failure)

    with pytest.raises(error_type):
        fetch.request_json_with_retries(URL, PARAMS)

    assert record.attempts == 4
    assert record.waits == [1, 2, 4]


def test_client_error_is_not_retried(fake_request):
    record = fake_request(NOT_FOUND)

    with pytest.raises(requests.exceptions.HTTPError):
        fetch.request_json_with_retries(URL, PARAMS)

    assert record.attempts == 1
    assert record.waits == []


def test_retry_stops_at_a_client_error(fake_request):
    record = fake_request(SERVER_ERROR, NOT_FOUND)

    with pytest.raises(requests.exceptions.HTTPError):
        fetch.request_json_with_retries(URL, PARAMS)

    assert record.attempts == 2
    assert record.waits == [1]

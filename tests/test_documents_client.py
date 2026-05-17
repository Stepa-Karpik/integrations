import httpx

from app.documents_client import HttpDocumentsClient


def test_documents_client_creates_watched_source():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/watched-sources"
        assert request.read()
        return httpx.Response(201, json={"id": "doc_wsrc_1"})

    client = HttpDocumentsClient(base_url="http://documents", transport=httpx.MockTransport(handler))
    result = client.create_watched_source(owner_subject_id="usr_1", provider="yandex_disk", root_path="/Docs")
    assert result["id"] == "doc_wsrc_1"

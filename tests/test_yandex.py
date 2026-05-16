import httpx

from app.yandex import YandexDiskClient, YandexOAuthClient


def test_builds_authorize_url_with_redirect_and_state():
    client = YandexOAuthClient(client_id='cid', client_secret='secret', redirect_uri='https://documents.example.com/callback')
    url = client.build_authorize_url(state='state_1')
    assert 'client_id=cid' in url
    assert 'response_type=code' in url
    assert 'state=state_1' in url


def test_lists_folder_files_from_yandex_disk_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/v1/disk/resources'
        return httpx.Response(200, json={'_embedded': {'items': [
            {'resource_id': 'disk_1', 'name': 'invoice.docx', 'revision': 7, 'type': 'file'},
            {'resource_id': 'folder_1', 'name': 'subfolder', 'type': 'dir'},
        ]}})
    client = YandexDiskClient(access_token='token', transport=httpx.MockTransport(handler))
    files = client.list_folder('/Docs')
    assert len(files) == 1
    assert files[0].external_file_id == 'disk_1'
    assert files[0].revision == '7'

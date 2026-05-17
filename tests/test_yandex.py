import httpx

from app.yandex import YandexDiskClient, YandexOAuthClient, decode_oauth_state, encode_oauth_state


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


def test_exchanges_code_for_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/token'
        return httpx.Response(200, json={'access_token': 'ya-token', 'refresh_token': 'ya-refresh', 'expires_in': 3600})
    client = YandexOAuthClient(client_id='cid', client_secret='secret', redirect_uri='https://documents.example.com/callback', transport=httpx.MockTransport(handler))
    token = client.exchange_code('code_1')
    assert token.access_token == 'ya-token'
    assert token.refresh_token == 'ya-refresh'


def test_oauth_state_round_trip_is_signed():
    state = encode_oauth_state(owner_subject_id="usr_1", secret="secret")
    assert decode_oauth_state(state, secret="secret") == "usr_1"

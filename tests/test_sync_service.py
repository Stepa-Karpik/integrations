from app.sync_service import YandexWatchedFolderSyncService
from app.yandex import ExternalFileSnapshot


class FakeYandex:
    ensured_path = None

    def ensure_folder(self, path):
        self.ensured_path = path

    def list_folder(self, path):
        assert path == '/Docs'
        return [ExternalFileSnapshot('disk_1', 'invoice.docx', 'rev_1', 'disk:/Docs/invoice.docx')]

class FakeDocuments:
    def __init__(self): self.calls=[]
    def sync_watched_source(self, source_id, files):
        self.calls.append((source_id, files))
        return [{'document_id': 'doc_1', 'action': 'created'}]


def test_sync_service_forwards_yandex_snapshot_to_documents():
    docs = FakeDocuments()
    yandex = FakeYandex()
    result = YandexWatchedFolderSyncService(yandex, docs).sync(source_id='source_1', root_path='/Docs')
    assert result[0]['action'] == 'created'
    assert docs.calls[0][0] == 'source_1'
    assert docs.calls[0][1][0]['external_file_id'] == 'disk_1'
    assert docs.calls[0][1][0]['external_path'] == 'disk:/Docs/invoice.docx'
    assert yandex.ensured_path == '/Docs'

from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from app.polling import YandexPollingWorker
from app.repositories import IntegrationRepository
from app.yandex import ExternalFileSnapshot


@dataclass
class FakeYandexClient:
    access_token: str

    def list_folder(self, path: str):
        assert path == "/Docs"
        return [ExternalFileSnapshot(external_file_id="disk_1", filename="invoice.pdf", revision="rev_1", external_path="disk:/Docs/invoice.pdf")]


class FakeDocumentsClient:
    def __init__(self):
        self.calls = []

    def sync_watched_source(self, source_id: str, files: list[dict]):
        self.calls.append((source_id, files))
        return [{"action": "created"}]


def test_polling_worker_syncs_linked_yandex_sources_and_completes_jobs():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repo = IntegrationRepository(Session(engine))
    connection = repo.create_yandex_connection(owner_subject_id="usr_1", access_token="token", refresh_token=None)
    source = repo.create_watched_source(
        owner_subject_id="usr_1",
        provider="yandex_disk",
        root_path="/Docs",
        connection_id=connection.id,
        downstream_source_id="doc_wsrc_1",
    )
    documents_client = FakeDocumentsClient()

    worker = YandexPollingWorker(
        repo,
        documents_client=documents_client,
        yandex_factory=lambda token: FakeYandexClient(access_token=token),
    )
    worker.poll_once()

    assert documents_client.calls == [
        (
            "doc_wsrc_1",
            [{"external_file_id": "disk_1", "filename": "invoice.pdf", "revision": "rev_1", "external_path": "disk:/Docs/invoice.pdf"}],
        )
    ]
    jobs = repo.list_sync_jobs(source.id)
    assert [job.status for job in jobs] == ["completed"]

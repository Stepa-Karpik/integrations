from collections.abc import Callable

from app.repositories import IntegrationRepository
from app.sync_service import YandexWatchedFolderSyncService
from app.yandex import YandexDiskClient


class YandexPollingWorker:
    def __init__(
        self,
        repo: IntegrationRepository,
        *,
        documents_client,
        yandex_factory: Callable[[str], object] | None = None,
    ):
        self.repo = repo
        self.documents_client = documents_client
        self.yandex_factory = yandex_factory or (lambda token: YandexDiskClient(access_token=token))

    def poll_once(self) -> None:
        for source in self.repo.list_all_watched_sources():
            if source.provider != "yandex_disk" or not source.connection_id or not source.downstream_source_id:
                continue
            connection = self.repo.get_connection(source.connection_id)
            if connection is None:
                continue
            job = self.repo.enqueue_sync_job(source_id=source.id)
            try:
                YandexWatchedFolderSyncService(
                    self.yandex_factory(connection.access_token),
                    self.documents_client,
                ).sync(source_id=source.downstream_source_id, root_path=source.root_path)
            except Exception:
                self.repo.fail_sync_job(job.id)
                continue
            self.repo.complete_sync_job(job.id)

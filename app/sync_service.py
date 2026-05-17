from typing import Protocol


class FolderSnapshotClient(Protocol):
    def list_folder(self, path: str): ...


class DocumentsSyncClient(Protocol):
    def sync_watched_source(self, source_id: str, files: list[dict]) -> list[dict]: ...


class YandexWatchedFolderSyncService:
    def __init__(self, yandex_client: FolderSnapshotClient, documents_client: DocumentsSyncClient):
        self.yandex_client = yandex_client
        self.documents_client = documents_client

    def sync(self, *, source_id: str, root_path: str) -> list[dict]:
        snapshots = self.yandex_client.list_folder(root_path)
        files = [
            {
                'external_file_id': snapshot.external_file_id,
                'filename': snapshot.filename,
                'revision': snapshot.revision,
                'external_path': snapshot.external_path,
            }
            for snapshot in snapshots
        ]
        return self.documents_client.sync_watched_source(source_id, files)

from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import UTC, datetime

from app.models import ConnectionModel, SyncJobModel, WatchedSourceModel


class IntegrationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_yandex_connection(self, *, owner_subject_id: str, access_token: str, refresh_token: str | None) -> ConnectionModel:
        connection = ConnectionModel(owner_subject_id=owner_subject_id, provider='yandex_disk', access_token=access_token, refresh_token=refresh_token)
        self.session.add(connection)
        self.session.commit()
        self.session.refresh(connection)
        return connection

    def list_connections(self, owner_subject_id: str) -> list[ConnectionModel]:
        return list(self.session.scalars(select(ConnectionModel).where(ConnectionModel.owner_subject_id == owner_subject_id)).all())

    def get_connection(self, connection_id: str) -> ConnectionModel | None:
        return self.session.get(ConnectionModel, connection_id)

    def create_watched_source(
        self,
        *,
        owner_subject_id: str,
        provider: str,
        root_path: str,
        connection_id: str | None = None,
        downstream_source_id: str | None = None,
    ) -> WatchedSourceModel:
        source = WatchedSourceModel(
            owner_subject_id=owner_subject_id,
            provider=provider,
            root_path=root_path,
            connection_id=connection_id,
            downstream_source_id=downstream_source_id,
        )
        self.session.add(source)
        self.session.commit()
        self.session.refresh(source)
        return source

    def list_watched_sources(self, owner_subject_id: str) -> list[WatchedSourceModel]:
        return list(self.session.scalars(select(WatchedSourceModel).where(WatchedSourceModel.owner_subject_id == owner_subject_id)).all())

    def list_all_watched_sources(self) -> list[WatchedSourceModel]:
        return list(self.session.scalars(select(WatchedSourceModel)).all())


class IntegrationRepository(IntegrationRepository):
    def enqueue_sync_job(self, *, source_id: str) -> SyncJobModel:
        job = SyncJobModel(source_id=source_id)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def complete_sync_job(self, job_id: str) -> SyncJobModel:
        job = self.session.get(SyncJobModel, job_id)
        assert job is not None
        job.status = 'completed'
        job.completed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(job)
        return job

    def list_sync_jobs(self, source_id: str) -> list[SyncJobModel]:
        return list(self.session.scalars(select(SyncJobModel).where(SyncJobModel.source_id == source_id)).all())

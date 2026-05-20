from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import UTC, datetime

from app.crypto import decrypt, encrypt
from app.models import ConnectionModel, ProviderCredentialModel, SyncJobModel, WatchedSourceModel


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

    def latest_connection(self, *, owner_subject_id: str, provider: str) -> ConnectionModel | None:
        stmt = select(ConnectionModel).where(
            ConnectionModel.owner_subject_id == owner_subject_id,
            ConnectionModel.provider == provider,
        ).order_by(ConnectionModel.created_at.desc())
        return self.session.scalar(stmt)

    def get_connection(self, connection_id: str) -> ConnectionModel | None:
        return self.session.get(ConnectionModel, connection_id)

    def upsert_provider_credentials(self, *, owner_subject_id: str, provider: str, client_id: str, client_secret: str) -> ProviderCredentialModel:
        credentials = self.get_provider_credentials(owner_subject_id=owner_subject_id, provider=provider)
        if credentials is None:
            credentials = ProviderCredentialModel(
                owner_subject_id=owner_subject_id,
                provider=provider,
                client_id_encrypted=encrypt(client_id),
                client_secret_encrypted=encrypt(client_secret),
            )
            self.session.add(credentials)
        else:
            credentials.client_id_encrypted = encrypt(client_id)
            credentials.client_secret_encrypted = encrypt(client_secret)
            credentials.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(credentials)
        return credentials

    def get_provider_credentials(self, *, owner_subject_id: str, provider: str) -> ProviderCredentialModel | None:
        return self.session.scalar(select(ProviderCredentialModel).where(
            ProviderCredentialModel.owner_subject_id == owner_subject_id,
            ProviderCredentialModel.provider == provider,
        ).order_by(ProviderCredentialModel.updated_at.desc()))

    def decrypt_provider_credentials(self, *, owner_subject_id: str, provider: str) -> tuple[str, str] | None:
        credentials = self.get_provider_credentials(owner_subject_id=owner_subject_id, provider=provider)
        if credentials is None:
            return None
        return decrypt(credentials.client_id_encrypted), decrypt(credentials.client_secret_encrypted)

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


    def latest_watched_source(self, *, owner_subject_id: str, provider: str) -> WatchedSourceModel | None:
        stmt = select(WatchedSourceModel).where(
            WatchedSourceModel.owner_subject_id == owner_subject_id,
            WatchedSourceModel.provider == provider,
        ).order_by(WatchedSourceModel.created_at.desc())
        return self.session.scalar(stmt)

    def update_watched_source(
        self,
        source: WatchedSourceModel,
        *,
        root_path: str,
        connection_id: str | None = None,
    ) -> WatchedSourceModel:
        source.root_path = root_path
        if connection_id is not None:
            source.connection_id = connection_id
        self.session.commit()
        self.session.refresh(source)
        return source

    def get_watched_source(self, source_id: str) -> WatchedSourceModel | None:
        return self.session.get(WatchedSourceModel, source_id)

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

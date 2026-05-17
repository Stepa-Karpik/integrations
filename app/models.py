from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ConnectionModel(Base):
    __tablename__ = 'connections'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f'conn_{uuid4().hex}')
    owner_subject_id: Mapped[str] = mapped_column(String(128), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    access_token: Mapped[str] = mapped_column(String(2048))
    refresh_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class WatchedSourceModel(Base):
    __tablename__ = 'watched_sources'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f'wsrc_{uuid4().hex}')
    owner_subject_id: Mapped[str] = mapped_column(String(128), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    root_path: Mapped[str] = mapped_column(String(1024))
    connection_id: Mapped[str | None] = mapped_column(ForeignKey('connections.id'), nullable=True)
    downstream_source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SyncJobModel(Base):
    __tablename__ = 'sync_jobs'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f'sjob_{uuid4().hex}')
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default='queued')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

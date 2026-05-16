from typing import Annotated
from fastapi import Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.repositories import IntegrationRepository

app = FastAPI(title='integrations')
SessionDep = Annotated[Session, Depends(get_session)]

class WatchedSourceCreate(BaseModel):
    owner_subject_id: str
    provider: str
    root_path: str
    connection_id: str | None = None

class YandexConnectionCreate(BaseModel):
    owner_subject_id: str
    access_token: str
    refresh_token: str | None = None

@app.get('/healthz')
def healthz(): return {'status': 'ok', 'service': 'integrations'}

@app.post('/api/v1/watched-sources', status_code=status.HTTP_201_CREATED)
def create_source(payload: WatchedSourceCreate, session: SessionDep):
    source = IntegrationRepository(session).create_watched_source(**payload.model_dump())
    return _source_to_dict(source)

@app.get('/api/v1/watched-sources')
def list_watched_sources(owner_subject_id: str, session: SessionDep):
    return [_source_to_dict(source) for source in IntegrationRepository(session).list_watched_sources(owner_subject_id)]

@app.post('/api/v1/connections/yandex-disk', status_code=status.HTTP_201_CREATED)
def create_yandex_connection(payload: YandexConnectionCreate, session: SessionDep):
    connection = IntegrationRepository(session).create_yandex_connection(**payload.model_dump())
    return _connection_to_dict(connection)

@app.get('/api/v1/connections')
def list_connections(owner_subject_id: str, session: SessionDep):
    return [_connection_to_dict(connection) for connection in IntegrationRepository(session).list_connections(owner_subject_id)]


def _connection_to_dict(connection):
    return {'id': connection.id, 'provider': connection.provider, 'owner_subject_id': connection.owner_subject_id, 'access_token': connection.access_token, 'refresh_token': connection.refresh_token}

def _source_to_dict(source):
    return {'id': source.id, 'owner_subject_id': source.owner_subject_id, 'provider': source.provider, 'root_path': source.root_path, 'connection_id': source.connection_id}

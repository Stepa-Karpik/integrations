import os
from typing import Annotated
from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.documents_client import HttpDocumentsClient
from app.repositories import IntegrationRepository

app = FastAPI(title='integrations')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in os.getenv('FRONTEND_ORIGINS', 'http://localhost:3200').split(',') if origin],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
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


def _build_documents_client() -> HttpDocumentsClient:
    return HttpDocumentsClient(base_url=os.getenv("DOCUMENTS_BASE_URL", "http://documents:8200"))

@app.get('/healthz')
def healthz(): return {'status': 'ok', 'service': 'integrations'}

@app.post('/api/v1/watched-sources', status_code=status.HTTP_201_CREATED)
def create_source(payload: WatchedSourceCreate, session: SessionDep):
    downstream_source = _build_documents_client().create_watched_source(
        owner_subject_id=payload.owner_subject_id,
        provider=payload.provider,
        root_path=payload.root_path,
    )
    source = IntegrationRepository(session).create_watched_source(
        **payload.model_dump(),
        downstream_source_id=downstream_source["id"],
    )
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
    return {'id': source.id, 'owner_subject_id': source.owner_subject_id, 'provider': source.provider, 'root_path': source.root_path, 'connection_id': source.connection_id, 'downstream_source_id': source.downstream_source_id}

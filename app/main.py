import os
from typing import Annotated
from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.documents_client import HttpDocumentsClient
from app.repositories import IntegrationRepository
from app.yandex import YandexOAuthClient, decode_oauth_state, encode_oauth_state

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


def _build_yandex_oauth_client() -> YandexOAuthClient:
    return YandexOAuthClient(
        client_id=os.getenv("YANDEX_DISK_CLIENT_ID", ""),
        client_secret=os.getenv("YANDEX_DISK_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("YANDEX_DISK_REDIRECT_URI", ""),
    )

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


@app.get('/api/v1/oauth/yandex-disk/authorize')
def authorize_yandex_disk(owner_subject_id: str):
    state = encode_oauth_state(
        owner_subject_id=owner_subject_id,
        secret=os.getenv("YANDEX_DISK_STATE_SECRET", os.getenv("YANDEX_DISK_CLIENT_SECRET", "dev-state-secret")),
    )
    return {"authorization_url": _build_yandex_oauth_client().build_authorize_url(state=state)}


@app.get('/api/v1/oauth/yandex-disk/callback')
def yandex_disk_callback(code: str, state: str, session: SessionDep):
    owner_subject_id = decode_oauth_state(
        state,
        secret=os.getenv("YANDEX_DISK_STATE_SECRET", os.getenv("YANDEX_DISK_CLIENT_SECRET", "dev-state-secret")),
    )
    token = _build_yandex_oauth_client().exchange_code(code)
    IntegrationRepository(session).create_yandex_connection(
        owner_subject_id=owner_subject_id,
        access_token=token.access_token,
        refresh_token=token.refresh_token,
    )
    return RedirectResponse(
        url=f"{os.getenv('DOCUMENTS_PUBLIC_BASE_URL', 'http://localhost:3200').rstrip('/')}/?integration=yandex-disk-connected"
    )


def _connection_to_dict(connection):
    return {'id': connection.id, 'provider': connection.provider, 'owner_subject_id': connection.owner_subject_id, 'access_token': connection.access_token, 'refresh_token': connection.refresh_token}

def _source_to_dict(source):
    return {'id': source.id, 'owner_subject_id': source.owner_subject_id, 'provider': source.provider, 'root_path': source.root_path, 'connection_id': source.connection_id, 'downstream_source_id': source.downstream_source_id}

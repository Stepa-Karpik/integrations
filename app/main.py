import os
from typing import Annotated
from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.documents_client import HttpDocumentsClient
from app.repositories import IntegrationRepository
from app.yandex import YandexDiskClient, YandexOAuthClient, decode_oauth_state, encode_oauth_state
from app.sync_service import YandexWatchedFolderSyncService

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

class YandexCredentialUpsert(BaseModel):
    owner_subject_id: str
    client_id: str
    client_secret: str

class YandexVerificationCodeExchange(BaseModel):
    owner_subject_id: str
    code: str


def _build_documents_client() -> HttpDocumentsClient:
    return HttpDocumentsClient(base_url=os.getenv("DOCUMENTS_BASE_URL", "http://documents:8200"))


def _build_yandex_oauth_client(*, client_id: str | None = None, client_secret: str | None = None) -> YandexOAuthClient:
    return YandexOAuthClient(
        client_id=client_id if client_id is not None else os.getenv("YANDEX_DISK_CLIENT_ID", ""),
        client_secret=client_secret if client_secret is not None else os.getenv("YANDEX_DISK_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("YANDEX_DISK_REDIRECT_URI", "") if os.getenv("YANDEX_DISK_INCLUDE_REDIRECT_URI", "false").lower() in {"1", "true", "yes"} else "",
    )

@app.get('/healthz')
def healthz(): return {'status': 'ok', 'service': 'integrations'}

@app.post('/api/v1/watched-sources', status_code=status.HTTP_201_CREATED)
def create_source(payload: WatchedSourceCreate, session: SessionDep):
    repo = IntegrationRepository(session)
    existing = repo.latest_watched_source(owner_subject_id=payload.owner_subject_id, provider=payload.provider)
    if existing is not None:
        source = repo.update_watched_source(existing, root_path=payload.root_path, connection_id=payload.connection_id)
        return _source_to_dict(source)

    downstream_source = _build_documents_client().create_watched_source(
        owner_subject_id=payload.owner_subject_id,
        provider=payload.provider,
        root_path=payload.root_path,
    )
    source = repo.create_watched_source(
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

@app.put('/api/v1/providers/yandex-disk/credentials')
def upsert_yandex_credentials(payload: YandexCredentialUpsert, session: SessionDep):
    IntegrationRepository(session).upsert_provider_credentials(
        owner_subject_id=payload.owner_subject_id,
        provider='yandex_disk',
        client_id=payload.client_id,
        client_secret=payload.client_secret,
    )
    return {'provider': 'yandex_disk', 'configured': True, 'client_id_hint': f'{payload.client_id[:4]}…'}

@app.get('/api/v1/providers/yandex-disk/status')
def yandex_disk_status(owner_subject_id: str, session: SessionDep):
    repo = IntegrationRepository(session)
    credentials = repo.get_provider_credentials(owner_subject_id=owner_subject_id, provider='yandex_disk')
    env_credentials_configured = bool(os.getenv("YANDEX_DISK_CLIENT_ID") and os.getenv("YANDEX_DISK_CLIENT_SECRET"))
    connection = repo.latest_connection(owner_subject_id=owner_subject_id, provider='yandex_disk')
    sources = repo.list_watched_sources(owner_subject_id)
    jobs = [job for source in sources for job in repo.list_sync_jobs(source.id)]
    last_job = max(jobs, key=lambda item: item.created_at, default=None)
    return {
        'provider': 'yandex_disk',
        'credentials_configured': credentials is not None or env_credentials_configured,
        'connected': connection is not None,
        'watched_sources': [_source_to_dict(source) for source in sources if source.provider == 'yandex_disk'],
        'last_sync_status': last_job.status if last_job else None,
        'last_sync_at': last_job.completed_at.isoformat() if last_job and last_job.completed_at else None,
    }


@app.post('/api/v1/external-files/upload', status_code=status.HTTP_201_CREATED)
async def upload_external_file(
    session: SessionDep,
    owner_subject_id: str = Form(...),
    provider: str = Form(...),
    root_path: str = Form('/Docs'),
    file: UploadFile = File(...),
):
    if provider != 'yandex_disk':
        raise HTTPException(status_code=400, detail='unsupported provider')
    connection = IntegrationRepository(session).latest_connection(owner_subject_id=owner_subject_id, provider=provider)
    if connection is None:
        raise HTTPException(status_code=409, detail='yandex disk is not connected')
    filename = file.filename or 'upload'
    snapshot = YandexDiskClient(access_token=connection.access_token).upload_file(
        folder_path=root_path,
        filename=filename,
        content=await file.read(),
    )
    return {
        'provider': provider,
        'external_file_id': snapshot.external_file_id,
        'external_path': snapshot.external_path,
        'filename': snapshot.filename,
        'revision': snapshot.revision,
        'content_type': file.content_type or 'application/octet-stream',
    }


@app.post('/api/v1/watched-sources/{source_id}/sync-now')
def sync_watched_source_now(source_id: str, session: SessionDep):
    repo = IntegrationRepository(session)
    source = repo.get_watched_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail='watched source not found')
    if source.provider != 'yandex_disk' or not source.connection_id or not source.downstream_source_id:
        raise HTTPException(status_code=409, detail='watched source is not connected')
    connection = repo.get_connection(source.connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail='connection not found')
    job = repo.enqueue_sync_job(source_id=source.id)
    result = YandexWatchedFolderSyncService(
        YandexDiskClient(access_token=connection.access_token),
        _build_documents_client(),
    ).sync(source_id=source.downstream_source_id, root_path=source.root_path)
    repo.complete_sync_job(job.id)
    return {'status': 'completed', 'items': result}


@app.get('/api/v1/external-files/content')
def download_external_file(owner_subject_id: str, provider: str, external_path: str, session: SessionDep):
    connection = IntegrationRepository(session).latest_connection(owner_subject_id=owner_subject_id, provider=provider)
    if connection is None:
        raise HTTPException(status_code=404, detail='connection not found')
    if provider != 'yandex_disk':
        raise HTTPException(status_code=400, detail='unsupported provider')
    content = YandexDiskClient(access_token=connection.access_token).download_file(external_path)
    return Response(content=content, media_type='application/octet-stream')


@app.get('/api/v1/oauth/yandex-disk/authorize')
def authorize_yandex_disk(owner_subject_id: str, session: SessionDep):
    credentials = IntegrationRepository(session).decrypt_provider_credentials(owner_subject_id=owner_subject_id, provider='yandex_disk')
    if credentials is None and os.getenv("YANDEX_DISK_CLIENT_ID") and os.getenv("YANDEX_DISK_CLIENT_SECRET"):
        credentials = (os.environ["YANDEX_DISK_CLIENT_ID"], os.environ["YANDEX_DISK_CLIENT_SECRET"])
    if credentials is None:
        raise HTTPException(status_code=409, detail='yandex credentials not configured')
    state = encode_oauth_state(
        owner_subject_id=owner_subject_id,
        secret=os.getenv("YANDEX_DISK_STATE_SECRET", os.getenv("YANDEX_DISK_CLIENT_SECRET", "dev-state-secret")),
    )
    return {"authorization_url": _build_yandex_oauth_client(client_id=credentials[0], client_secret=credentials[1]).build_authorize_url(state=state)}


@app.post('/api/v1/oauth/yandex-disk/verification-code')
def exchange_yandex_disk_verification_code(payload: YandexVerificationCodeExchange, session: SessionDep):
    credentials = IntegrationRepository(session).decrypt_provider_credentials(owner_subject_id=payload.owner_subject_id, provider='yandex_disk')
    if credentials is None and os.getenv("YANDEX_DISK_CLIENT_ID") and os.getenv("YANDEX_DISK_CLIENT_SECRET"):
        credentials = (os.environ["YANDEX_DISK_CLIENT_ID"], os.environ["YANDEX_DISK_CLIENT_SECRET"])
    if credentials is None:
        raise HTTPException(status_code=409, detail='yandex credentials not configured')
    token = _build_yandex_oauth_client(client_id=credentials[0], client_secret=credentials[1]).exchange_code(payload.code.strip())
    connection = IntegrationRepository(session).create_yandex_connection(
        owner_subject_id=payload.owner_subject_id,
        access_token=token.access_token,
        refresh_token=token.refresh_token,
    )
    return _connection_to_dict(connection)


@app.get('/api/v1/oauth/yandex-disk/callback')
def yandex_disk_callback(code: str, state: str, session: SessionDep):
    owner_subject_id = decode_oauth_state(
        state,
        secret=os.getenv("YANDEX_DISK_STATE_SECRET", os.getenv("YANDEX_DISK_CLIENT_SECRET", "dev-state-secret")),
    )
    credentials = IntegrationRepository(session).decrypt_provider_credentials(owner_subject_id=owner_subject_id, provider='yandex_disk')
    if credentials is None and os.getenv("YANDEX_DISK_CLIENT_ID") and os.getenv("YANDEX_DISK_CLIENT_SECRET"):
        credentials = (os.environ["YANDEX_DISK_CLIENT_ID"], os.environ["YANDEX_DISK_CLIENT_SECRET"])
    oauth_client = _build_yandex_oauth_client(client_id=credentials[0], client_secret=credentials[1]) if credentials is not None else _build_yandex_oauth_client()
    token = oauth_client.exchange_code(code)
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

from uuid import uuid4
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI(title="integrations")
connections: list[dict] = []
class WatchedSourceCreate(BaseModel):
    owner_subject_id: str
    provider: str
    root_path: str

class YandexConnectionCreate(BaseModel):
    owner_subject_id: str
    access_token: str
    refresh_token: str | None = None
@app.get('/healthz')
def healthz(): return {'status': 'ok', 'service': 'integrations'}
@app.post('/api/v1/watched-sources', status_code=status.HTTP_201_CREATED)
def create_source(payload: WatchedSourceCreate):
    return {'id': f'wsrc_{uuid4().hex}', **payload.model_dump()}


@app.post('/api/v1/connections/yandex-disk', status_code=status.HTTP_201_CREATED)
def create_yandex_connection(payload: YandexConnectionCreate):
    connection = {'id': f'conn_{uuid4().hex}', 'provider': 'yandex_disk', **payload.model_dump()}
    connections.append(connection)
    return connection

@app.get('/api/v1/connections')
def list_connections(owner_subject_id: str):
    return [connection for connection in connections if connection['owner_subject_id'] == owner_subject_id]

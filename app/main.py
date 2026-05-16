from uuid import uuid4
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI(title="integrations")
class WatchedSourceCreate(BaseModel):
    owner_subject_id: str
    provider: str
    root_path: str
@app.get('/healthz')
def healthz(): return {'status': 'ok', 'service': 'integrations'}
@app.post('/api/v1/watched-sources', status_code=status.HTTP_201_CREATED)
def create_source(payload: WatchedSourceCreate):
    return {'id': f'wsrc_{uuid4().hex}', **payload.model_dump()}

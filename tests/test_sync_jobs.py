from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from app.repositories import IntegrationRepository


def test_sync_job_can_be_enqueued_and_completed():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    repo = IntegrationRepository(Session(engine))
    job = repo.enqueue_sync_job(source_id='source_1')
    assert job.status == 'queued'
    completed = repo.complete_sync_job(job.id)
    assert completed.status == 'completed'

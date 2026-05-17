import os
import time

from app.db import SessionLocal
from app.documents_client import HttpDocumentsClient
from app.polling import YandexPollingWorker
from app.repositories import IntegrationRepository


def main() -> None:
    interval_seconds = int(os.getenv("YANDEX_DISK_POLL_INTERVAL_SECONDS", "120"))
    while True:
        with SessionLocal() as session:
            YandexPollingWorker(
                IntegrationRepository(session),
                documents_client=HttpDocumentsClient(base_url=os.getenv("DOCUMENTS_BASE_URL", "http://documents:8200")),
            ).poll_once()
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()

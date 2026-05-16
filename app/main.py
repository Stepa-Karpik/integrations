from fastapi import FastAPI

app = FastAPI(title="integrations")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "integrations"}

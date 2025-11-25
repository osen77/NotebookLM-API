"""FastAPI application for NotebookLM Automator."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from notebooklm_automator.api.routes import router, get_automator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    yield

    try:
        automator = get_automator()
        automator.close()
    except Exception:
        pass


app = FastAPI(title="NotebookLM Automator API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

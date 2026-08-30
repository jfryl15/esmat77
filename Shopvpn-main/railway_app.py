"""ASGI entry point for Railway.

Railway exposes one HTTP port per service.  This app hosts the Telegram Mini
App at / and the independent web admin panel at /admin, while its lifespan
also runs the Telegram long-polling workers in the same service.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException

from admin_panel.server import app as admin_panel_app
from main import main as run_bots
from miniapp.server import app as miniapp_app

logger = logging.getLogger("railway_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do not wait for Telegram during startup: Railway must be able to reach
    # the health endpoint even if Telegram is temporarily unavailable.
    task = asyncio.create_task(run_bots(), name="telegram-bots")
    app.state.bot_task = task
    try:
        yield
    finally:
        task.cancel()
        # Do not turn a prior bot failure into an ASGI shutdown error.
        with suppress(asyncio.CancelledError, Exception):
            await task


app = FastAPI(title="ShopVPN Railway Service", lifespan=lifespan)


@app.get("/health", include_in_schema=False)
async def healthcheck():
    task = getattr(app.state, "bot_task", None)
    if task and task.done():
        exc = None if task.cancelled() else task.exception()
        logger.error("Telegram worker stopped unexpectedly: %r", exc)
        raise HTTPException(status_code=503, detail="Telegram worker is not running")
    return {"status": "ok"}


# Specific prefix must be mounted before /, otherwise Mini App's static route
# would receive requests intended for the admin panel.
app.mount("/admin", admin_panel_app)
app.mount("/", miniapp_app)

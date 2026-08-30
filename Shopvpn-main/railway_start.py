"""Starts the Railway ASGI service on the port supplied by Railway."""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "railway_app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        proxy_headers=True,
    )

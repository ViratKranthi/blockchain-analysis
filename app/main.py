"""Entry point — `python -m app.main` or `uvicorn app.api:app`."""
from __future__ import annotations

import uvicorn

from app.config import settings


def main() -> None:
    uvicorn.run(
        "app.api:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()

"""`python -m workout_tracker` — start the dev server."""

import logging
import os

from workout_tracker.app import create_app

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("DEBUG", "0") == "1"
    create_app().run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()

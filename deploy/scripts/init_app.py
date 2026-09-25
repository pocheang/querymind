"""Initialise the application databases: every schema migration, then the one-time tasks.

The work lives in `app/init_app.py` so it ships in the backend image, which does
not contain `deploy/`. Inside a container run `python -m app.init_app`; this
wrapper is for a checkout.
"""

from app.init_app import main

if __name__ == "__main__":
    raise SystemExit(main())

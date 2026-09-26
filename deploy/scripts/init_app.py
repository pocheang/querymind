"""Initialise the application databases: every schema migration, then the one-time tasks.

The work lives in `app/init_app.py`; this is a wrapper for a checkout. In a
container run `python -m app.init_app`, which is what the deploy scripts do.
"""

from app.init_app import main

if __name__ == "__main__":
    raise SystemExit(main())

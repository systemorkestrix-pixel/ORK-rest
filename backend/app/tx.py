from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def transaction_scope(db: Session) -> Iterator[None]:
    if db.in_nested_transaction():
        with db.begin_nested():
            yield
        return

    if db.in_transaction():
        try:
            yield
            db.commit()
        except Exception:
            db.rollback()
            raise
        return

    else:
        with db.begin():
            yield

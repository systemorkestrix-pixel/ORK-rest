import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase5-perf-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.models import Order, RestaurantTable
from application.operations_engine.domain.table_sessions import (
    list_active_table_sessions,
    list_tables_with_session_summary,
)


class _SelectQueryCounter:
    def __init__(self, engine):
        self._engine = engine
        self.count = 0

    def _before_cursor_execute(self, _conn, _cursor, statement, _params, _context, _executemany):
        text = str(statement).lstrip().upper()
        if text.startswith("SELECT"):
            self.count += 1

    def __enter__(self):
        event.listen(self._engine, "before_cursor_execute", self._before_cursor_execute)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        event.remove(self._engine, "before_cursor_execute", self._before_cursor_execute)


class Phase5PerformanceTests(unittest.TestCase):
    def _build_migrated_session(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"alembic upgrade failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        engine = create_app_engine(f"sqlite:///{db_path.as_posix()}")
        session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
        return session, engine, db_path

    def _seed_tables_and_orders(self, db) -> None:
        tables: list[RestaurantTable] = []
        for idx in range(1, 26):
            table = RestaurantTable(
                qr_code=f"/menu?table={idx}",
                status="available",
            )
            db.add(table)
            tables.append(table)
        db.flush()

        # Open dine-in sessions (10 tables): 5 in-progress + 5 delivered unpaid.
        for idx in range(0, 5):
            db.add(
                Order(
                    type="dine-in",
                    status="CREATED",
                    table_id=int(tables[idx].id),
                    subtotal=20.0,
                    delivery_fee=0.0,
                    total=20.0,
                    payment_status="unpaid",
                    payment_method="cash",
                )
            )
        for idx in range(5, 10):
            db.add(
                Order(
                    type="dine-in",
                    status="DELIVERED",
                    table_id=int(tables[idx].id),
                    subtotal=15.0,
                    delivery_fee=0.0,
                    total=15.0,
                    payment_status="unpaid",
                    payment_method="cash",
                )
            )

        # Closed sessions (5 tables): delivered and paid.
        for idx in range(10, 15):
            db.add(
                Order(
                    type="dine-in",
                    status="DELIVERED",
                    table_id=int(tables[idx].id),
                    subtotal=12.0,
                    delivery_fee=0.0,
                    total=12.0,
                    payment_status="paid",
                    payment_method="cash",
                )
            )
        db.commit()

    def test_list_tables_with_session_summary_avoids_n_plus_one(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            self._seed_tables_and_orders(db)
            with _SelectQueryCounter(engine) as counter:
                rows = list_tables_with_session_summary(db)

            self.assertEqual(len(rows), 25)
            active_sessions = sum(1 for row in rows if bool(row["has_active_session"]))
            self.assertEqual(active_sessions, 10)
            self.assertLessEqual(
                counter.count,
                3,
                msg=f"Expected constant query count for table summary, got {counter.count} SELECT statements.",
            )
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_list_active_table_sessions_avoids_n_plus_one(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            self._seed_tables_and_orders(db)
            with _SelectQueryCounter(engine) as counter:
                sessions = list_active_table_sessions(db)

            self.assertEqual(len(sessions), 10)
            self.assertTrue(all(bool(session["has_active_session"]) for session in sessions))
            self.assertLessEqual(
                counter.count,
                2,
                msg=f"Expected constant query count for active sessions, got {counter.count} SELECT statements.",
            )
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()

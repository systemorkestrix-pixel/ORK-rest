import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase3-test-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.models import User, WarehouseIntegrationEvent
from app.warehouse_services import (
    consume_pending_warehouse_integration_events,
    create_warehouse_inbound_voucher,
    create_warehouse_item,
    create_warehouse_outbound_voucher,
    create_warehouse_stock_count,
    create_warehouse_supplier,
    settle_warehouse_stock_count,
    update_warehouse_supplier,
)


class Phase3IntegrationEventsTests(unittest.TestCase):
    def _build_migrated_session(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        env = os.environ.copy()
        env["DATABASE_PATH"] = db_path.as_posix()
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

    def _seed_actor(self, db) -> User:
        actor = User(
            name="Phase3 Manager",
            username="phase3_manager",
            password_hash="$argon2id$seed",
            role="manager",
            active=True,
        )
        db.add(actor)
        db.commit()
        db.refresh(actor)
        return actor

    def _seed_supplier_and_item(self, db):
        supplier = create_warehouse_supplier(
            db,
            name="Phase3 Supplier",
            phone=None,
            email=None,
            address=None,
            payment_term_days=0,
            credit_limit=None,
            quality_rating=4.5,
            lead_time_days=1,
            notes=None,
            active=True,
            supplied_item_ids=[],
        )
        item = create_warehouse_item(
            db,
            name="Phase3 Item",
            unit="kg",
            alert_threshold=1.0,
            active=True,
        )
        update_warehouse_supplier(
            db,
            supplier_id=int(supplier["id"]),
            name=str(supplier["name"]),
            phone=supplier.get("phone"),
            email=supplier.get("email"),
            address=supplier.get("address"),
            payment_term_days=int(supplier["payment_term_days"]),
            credit_limit=supplier.get("credit_limit"),
            quality_rating=float(supplier["quality_rating"]),
            lead_time_days=int(supplier["lead_time_days"]),
            notes=supplier.get("notes"),
            active=bool(supplier["active"]),
            supplied_item_ids=[int(item.id)],
        )
        return supplier, item

    def test_inbound_event_is_consumed_without_pending(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._seed_actor(db)
            supplier, item = self._seed_supplier_and_item(db)

            voucher = create_warehouse_inbound_voucher(
                db,
                supplier_id=int(supplier["id"]),
                reference_no="PO-001",
                note="Inbound for phase3",
                idempotency_key=None,
                items=[(int(item.id), 10.0, 2.5)],
                actor_id=int(actor.id),
            )
            db.commit()

            event = db.execute(
                select(WarehouseIntegrationEvent).where(
                    WarehouseIntegrationEvent.source_type == "wh_inbound_voucher",
                    WarehouseIntegrationEvent.source_id == int(voucher["id"]),
                )
            ).scalar_one()
            self.assertEqual(event.status, "processed")
            self.assertIsNotNone(event.processed_at)
            self.assertIsNone(event.last_error)

            pending_count = int(
                db.execute(
                    select(func.count(WarehouseIntegrationEvent.id)).where(
                        WarehouseIntegrationEvent.status == "pending"
                    )
                ).scalar_one()
            )
            self.assertEqual(pending_count, 0)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_outbound_and_stock_count_events_are_consumed(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._seed_actor(db)
            supplier, item = self._seed_supplier_and_item(db)

            create_warehouse_inbound_voucher(
                db,
                supplier_id=int(supplier["id"]),
                reference_no="PO-002",
                note="Seed stock",
                idempotency_key=None,
                items=[(int(item.id), 8.0, 3.0)],
                actor_id=int(actor.id),
            )
            create_warehouse_outbound_voucher(
                db,
                reason_code="operational_use",
                reason_note=None,
                note="Kitchen usage",
                idempotency_key=None,
                items=[(int(item.id), 2.0)],
                actor_id=int(actor.id),
            )
            count_doc = create_warehouse_stock_count(
                db,
                note="Daily stock count",
                idempotency_key=None,
                items=[(int(item.id), 5.0)],
                actor_id=int(actor.id),
            )
            settle_warehouse_stock_count(
                db,
                count_id=int(count_doc["id"]),
                actor_id=int(actor.id),
            )
            db.commit()

            events = db.execute(
                select(WarehouseIntegrationEvent).order_by(WarehouseIntegrationEvent.id.asc())
            ).scalars().all()
            self.assertEqual(len(events), 3)
            self.assertTrue(all(event.status == "processed" for event in events))
            self.assertTrue(all(event.processed_at is not None for event in events))

            pending_count = int(
                db.execute(
                    select(func.count(WarehouseIntegrationEvent.id)).where(
                        WarehouseIntegrationEvent.status == "pending"
                    )
                ).scalar_one()
            )
            self.assertEqual(pending_count, 0)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_unknown_event_transitions_to_failed_not_pending(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            db.add(
                WarehouseIntegrationEvent(
                    event_type="unknown_event_type",
                    source_type="unknown_source",
                    source_id=999,
                    payload_json="{}",
                    status="pending",
                )
            )
            stats = consume_pending_warehouse_integration_events(db, limit=100)
            db.commit()

            self.assertEqual(stats["failed"], 1)
            self.assertEqual(stats["processed"], 0)

            failed_event = db.execute(select(WarehouseIntegrationEvent)).scalar_one()
            self.assertEqual(failed_event.status, "failed")
            self.assertIsNotNone(failed_event.last_error)
            self.assertIsNotNone(failed_event.processed_at)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_create_item_requires_at_least_one_active_supplier(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            with self.assertRaises(HTTPException) as failure:
                create_warehouse_item(
                    db,
                    name="No Supplier Item",
                    unit="kg",
                    alert_threshold=1.0,
                    active=True,
                )
            self.assertEqual(failure.exception.status_code, 400)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_inbound_rejects_items_not_linked_to_selected_supplier(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._seed_actor(db)
            supplier_a = create_warehouse_supplier(
                db,
                name="Supplier A",
                phone=None,
                email=None,
                address=None,
                payment_term_days=0,
                credit_limit=None,
                quality_rating=4.0,
                lead_time_days=1,
                notes=None,
                active=True,
                supplied_item_ids=[],
            )
            supplier_b = create_warehouse_supplier(
                db,
                name="Supplier B",
                phone=None,
                email=None,
                address=None,
                payment_term_days=0,
                credit_limit=None,
                quality_rating=4.0,
                lead_time_days=1,
                notes=None,
                active=True,
                supplied_item_ids=[],
            )
            item = create_warehouse_item(
                db,
                name="Linked Item",
                unit="kg",
                alert_threshold=0.0,
                active=True,
            )
            update_warehouse_supplier(
                db,
                supplier_id=int(supplier_a["id"]),
                name=str(supplier_a["name"]),
                phone=supplier_a.get("phone"),
                email=supplier_a.get("email"),
                address=supplier_a.get("address"),
                payment_term_days=int(supplier_a["payment_term_days"]),
                credit_limit=supplier_a.get("credit_limit"),
                quality_rating=float(supplier_a["quality_rating"]),
                lead_time_days=int(supplier_a["lead_time_days"]),
                notes=supplier_a.get("notes"),
                active=bool(supplier_a["active"]),
                supplied_item_ids=[int(item.id)],
            )
            db.commit()

            with self.assertRaises(HTTPException) as failure:
                create_warehouse_inbound_voucher(
                    db,
                    supplier_id=int(supplier_b["id"]),
                    reference_no="PO-UNLINKED",
                    note="must fail",
                    idempotency_key=None,
                    items=[(int(item.id), 1.0, 2.0)],
                    actor_id=int(actor.id),
                )
            self.assertEqual(failure.exception.status_code, 400)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_outbound_requires_prior_inbound_movement(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._seed_actor(db)
            _supplier, item = self._seed_supplier_and_item(db)
            count_doc = create_warehouse_stock_count(
                db,
                note="stock count without inbound",
                idempotency_key=None,
                items=[(int(item.id), 5.0)],
                actor_id=int(actor.id),
            )
            settle_warehouse_stock_count(
                db,
                count_id=int(count_doc["id"]),
                actor_id=int(actor.id),
            )
            db.commit()

            with self.assertRaises(HTTPException) as failure:
                create_warehouse_outbound_voucher(
                    db,
                    reason_code="kitchen_supply",
                    reason_note=None,
                    note="must fail without inbound",
                    idempotency_key=None,
                    items=[(int(item.id), 1.0)],
                    actor_id=int(actor.id),
                )
            self.assertEqual(failure.exception.status_code, 400)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()

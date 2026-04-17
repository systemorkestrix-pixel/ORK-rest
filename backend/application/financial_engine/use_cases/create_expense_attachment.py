from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import ExpenseAttachment
from app.schemas import ExpenseAttachmentCreate, ExpenseAttachmentOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_expense_attachment(
        self,
        *,
        expense_id: int,
        file_name: str | None,
        mime_type: str,
        data_base64: str,
        uploaded_by: int,
    ) -> ExpenseAttachment:
        ...


@dataclass
class Input:
    actor_id: int
    expense_id: int
    payload: ExpenseAttachmentCreate


@dataclass
class Output:
    result: ExpenseAttachmentOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        attachment = repo.create_expense_attachment(
            expense_id=data.expense_id,
            file_name=data.payload.file_name,
            mime_type=data.payload.mime_type,
            data_base64=data.payload.data_base64,
            uploaded_by=data.actor_id,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.SYSTEM_AUDIT_RECORDED,
                payload={
                    "entity_type": "expense_attachment",
                    "entity_id": int(attachment.id),
                    "expense_id": int(attachment.expense_id),
                    "action": "expense_attachment_added",
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=attachment)

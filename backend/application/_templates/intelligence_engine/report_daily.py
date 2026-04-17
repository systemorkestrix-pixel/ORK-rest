"""
Use Case: ReportDaily (Intelligence Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class ReportingRepository(Protocol):
    def report_daily(self, *args, **kwargs):
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    rows: list[dict]


def execute(*, data: Input, repo: ReportingRepository) -> Output:
    rows = repo.report_daily(page=data.page, page_size=data.page_size)
    return Output(rows=rows)

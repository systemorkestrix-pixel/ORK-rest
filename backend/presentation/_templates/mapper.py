"""
Mapper Template

Rules:
- Convert legacy request/response payloads to internal DTOs and back.
- No domain logic here.
"""

from dataclasses import dataclass


@dataclass
class LegacyRequest:
    # TODO: define fields
    pass


@dataclass
class InternalDTO:
    # TODO: define fields
    pass


@dataclass
class LegacyResponse:
    # TODO: define fields
    pass


def map_request(payload: LegacyRequest) -> InternalDTO:
    # TODO: map legacy request to internal DTO
    return InternalDTO()


def map_response(dto: InternalDTO) -> LegacyResponse:
    # TODO: map internal DTO to legacy response
    return LegacyResponse()

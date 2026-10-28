"""Tests for route handler error conversion."""

import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from api.routes.helpers import handle_route_errors


class ResponseModel(BaseModel):
    value: int


@handle_route_errors()
def sync_route_with_invalid_response():
    return ResponseModel(value="invalid")


@handle_route_errors()
async def async_route_with_invalid_response():
    return ResponseModel(value="invalid")


def test_sync_response_validation_error_is_internal_error():
    with pytest.raises(HTTPException) as exc_info:
        sync_route_with_invalid_response()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "An internal error occurred. Please try again later."


@pytest.mark.asyncio
async def test_async_response_validation_error_is_internal_error():
    with pytest.raises(HTTPException) as exc_info:
        await async_route_with_invalid_response()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "An internal error occurred. Please try again later."

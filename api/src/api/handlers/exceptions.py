from litestar import MediaType, Request, Response
from sqlspec.exceptions import IntegrityError, NotFoundError, UniqueViolationError


def sqlspec_unique_violation_handler(_: Request, exc: UniqueViolationError) -> Response:  # noqa: ARG001
    return Response(
        status_code=409,
        content="Request data conflict",
        media_type=MediaType.TEXT,
    )


def sqlspec_integrity_error_handler(_: Request, exc: IntegrityError) -> Response:  # noqa: ARG001
    return Response(
        status_code=400,
        content="Request validation failed",
        media_type=MediaType.TEXT,
    )


def sqlspec_not_found_handler(_: Request, exc: NotFoundError) -> Response:  # noqa: ARG001
    return Response(
        status_code=404,
        content="Item not found",
        media_type=MediaType.TEXT,
    )


exception_handlers = {
    UniqueViolationError: sqlspec_unique_violation_handler,
    IntegrityError: sqlspec_integrity_error_handler,
    NotFoundError: sqlspec_not_found_handler,
}

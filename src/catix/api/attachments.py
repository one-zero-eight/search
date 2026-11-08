"""Authenticated binary uploads; originals never have a public URL."""
import re
from urllib.parse import quote, unquote

from fastapi import APIRouter, Header, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from catix import attachments
from catix.api.auth import VerifiedDep
from catix.attachments import AttachmentError, AttachmentInfo

router = APIRouter(tags=["Ask"])
BINARY = {"content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}


@router.post("/ask/attachments", response_model=AttachmentInfo,
             openapi_extra={"requestBody": {"required": True, **BINARY}})
async def upload(request: Request, user: VerifiedDep, filename: str = Header(
    ..., alias="X-Attachment-Filename", description="UTF-8 filename encoded once with encodeURIComponent (percent encoding).",
)) -> AttachmentInfo:
    if not filename.isascii() or re.search(r"%(?![0-9A-Fa-f]{2})", filename):
        raise HTTPException(400, "Invalid attachment filename header.")
    try:
        filename = unquote(filename, encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        raise HTTPException(400, "Invalid attachment filename header.") from None
    if not 1 <= len(filename) <= 200:
        raise HTTPException(400, "Invalid attachment filename header.")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/octet-stream":
        raise HTTPException(415, "Send raw file bytes as application/octet-stream.")
    if length := request.headers.get("content-length"):
        try:
            size = int(length)
        except ValueError:
            raise HTTPException(400, "Invalid Content-Length.") from None
        if size < 0:
            raise HTTPException(400, "Invalid Content-Length.")
        if size > attachments.MAX_BYTES:
            raise HTTPException(413, "Each attachment must be at most 10 MiB.")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > attachments.MAX_BYTES:
            raise HTTPException(413, "Each attachment must be at most 10 MiB.")
        data.extend(chunk)
    try:
        return await run_in_threadpool(attachments.create, user.innohassle_id, filename, bytes(data))
    except AttachmentError as error:
        raise HTTPException(error.status_code, error.detail) from None


@router.get("/ask/attachments/{attachment_id}/content", response_class=Response,
            responses={200: {"description": "Private attachment original", **BINARY}})
async def content(attachment_id: str, user: VerifiedDep) -> Response:
    try:
        info, data = await run_in_threadpool(attachments.get_content, user.innohassle_id, attachment_id)
    except AttachmentError as error:
        raise HTTPException(error.status_code, error.detail) from None
    return Response(data, media_type=info.media_type, headers={
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(info.filename, safe=""),
    })


@router.delete("/ask/attachments/{attachment_id}", status_code=204, response_class=Response)
async def delete(attachment_id: str, user: VerifiedDep) -> Response:
    try:
        deleted = await run_in_threadpool(attachments.discard, user.innohassle_id, attachment_id)
    except AttachmentError as error:
        raise HTTPException(error.status_code, error.detail) from None
    if not deleted:
        raise HTTPException(404, "Attachment not found.")
    return Response(status_code=204)

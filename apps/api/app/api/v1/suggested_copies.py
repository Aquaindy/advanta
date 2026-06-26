from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.exceptions import AdVantaError
from app.db.session import get_db
from app.models.suggested_copy import SuggestedCopyType
from app.models.workspace_member import WorkspaceMember
from app.schemas.agents import AgentRunDetail
from app.schemas.suggested_copy import (
    GenerateSuggestedCopiesRequest,
    SuggestedCopyPublic,
)
from app.security.dependencies import get_current_member, require_role
from app.security.permissions import Role
from app.services import suggested_copy_service
from app.services.agent_service import get_run_detail
from app.workers.dispatch import run_or_dispatch
from app.workers.tasks import run_agent_task

router = APIRouter()


class SuggestedCopyNotFoundError(AdVantaError):
    status_code = 404
    code = "suggested_copy_not_found"


class NoSuggestedCopiesError(AdVantaError):
    status_code = 404
    code = "no_suggested_copies"


class UnsupportedFormatError(AdVantaError):
    status_code = 400
    code = "unsupported_format"


# ---------------------------------------------------------------------------
# List + generate (static paths declared before "/{copy_id}")
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/suggested-copies",
    response_model=list[SuggestedCopyPublic],
)
def list_suggested_copies_endpoint(
    workspace_id: UUID,
    copy_type: SuggestedCopyType | None = Query(default=None),
    profile_id: UUID | None = Query(default=None),
    _member: WorkspaceMember = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> list[SuggestedCopyPublic]:
    rows = suggested_copy_service.list_suggested_copies(
        db, workspace_id=workspace_id, copy_type=copy_type, profile_id=profile_id
    )
    return [SuggestedCopyPublic.model_validate(r) for r in rows]


@router.post(
    "/{workspace_id}/suggested-copies/generate",
    response_model=AgentRunDetail,
    status_code=status.HTTP_201_CREATED,
)
def generate_suggested_copies_endpoint(
    workspace_id: UUID,
    payload: GenerateSuggestedCopiesRequest,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> AgentRunDetail:
    # Route through the agent runtime (run_or_dispatch) so the work is billed
    # (AI credits), persisted, and traceable exactly like any other agent run.
    input_payload: dict = {}
    if payload.product_name and payload.product_name.strip():
        input_payload["product_name"] = payload.product_name.strip()
    if payload.profile_id is not None:
        input_payload["growth_dna_profile_id"] = str(payload.profile_id)

    result = run_or_dispatch(
        run_agent_task,
        workspace_id=str(workspace_id),
        agent_type="growth_content",
        triggered_by_user_id=str(member.user_id),
        input_payload=input_payload,
    )
    data = result.get(timeout=300)
    run_id = UUID(data["run_id"])
    detail = get_run_detail(db, workspace_id=workspace_id, run_id=run_id)
    assert detail is not None  # task just created it
    return detail


@router.get("/{workspace_id}/suggested-copies/download")
def download_all_suggested_copies(
    workspace_id: UUID,
    fmt: str = Query(default="docx", alias="format"),
    copy_type: SuggestedCopyType | None = Query(default=None),
    profile_id: UUID | None = Query(default=None),
    _member: WorkspaceMember = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> Response:
    rows = suggested_copy_service.list_suggested_copies(
        db, workspace_id=workspace_id, copy_type=copy_type, profile_id=profile_id
    )
    if not rows:
        raise NoSuggestedCopiesError("No suggested copies to download yet.")

    product_name = rows[0].product_name
    base = suggested_copy_service.safe_filename("suggested_copies", product_name)
    fmt_lower = fmt.lower()
    if fmt_lower == "txt":
        body = suggested_copy_service.render_bundle_txt(rows, product_name=product_name)
        return _file_response(body, "text/plain; charset=utf-8", f"{base}.txt")
    if fmt_lower == "docx":
        body = suggested_copy_service.render_bundle_docx(rows, product_name=product_name)
        return _file_response(body, suggested_copy_service.DOCX_MEDIA_TYPE, f"{base}.docx")
    raise UnsupportedFormatError("Use ?format=txt or ?format=docx.")


# ---------------------------------------------------------------------------
# Single-copy fetch / download / delete
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/suggested-copies/{copy_id}",
    response_model=SuggestedCopyPublic,
)
def get_suggested_copy_endpoint(
    workspace_id: UUID,
    copy_id: UUID,
    _member: WorkspaceMember = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> SuggestedCopyPublic:
    row = suggested_copy_service.get_suggested_copy(
        db, workspace_id=workspace_id, copy_id=copy_id
    )
    if row is None:
        raise SuggestedCopyNotFoundError("Suggested copy not found in this workspace.")
    return SuggestedCopyPublic.model_validate(row)


@router.get("/{workspace_id}/suggested-copies/{copy_id}/download")
def download_suggested_copy(
    workspace_id: UUID,
    copy_id: UUID,
    fmt: str = Query(default="txt", alias="format"),
    _member: WorkspaceMember = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> Response:
    row = suggested_copy_service.get_suggested_copy(
        db, workspace_id=workspace_id, copy_id=copy_id
    )
    if row is None:
        raise SuggestedCopyNotFoundError("Suggested copy not found in this workspace.")

    base = suggested_copy_service.safe_filename(row.copy_type.value, row.title)
    fmt_lower = fmt.lower()
    if fmt_lower == "txt":
        body = suggested_copy_service.render_txt(row)
        return _file_response(body, "text/plain; charset=utf-8", f"{base}.txt")
    if fmt_lower == "docx":
        body = suggested_copy_service.render_docx(row)
        return _file_response(body, suggested_copy_service.DOCX_MEDIA_TYPE, f"{base}.docx")
    raise UnsupportedFormatError("Use ?format=txt or ?format=docx.")


@router.delete(
    "/{workspace_id}/suggested-copies/{copy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_suggested_copy_endpoint(
    workspace_id: UUID,
    copy_id: UUID,
    _member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> Response:
    deleted = suggested_copy_service.delete_suggested_copy(
        db, workspace_id=workspace_id, copy_id=copy_id
    )
    if not deleted:
        raise SuggestedCopyNotFoundError("Suggested copy not found in this workspace.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _file_response(body: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

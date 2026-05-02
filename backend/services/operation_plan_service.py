from datetime import datetime, timezone


APPROVAL_ROLES = {"admin", "approver"}


class OperationPlanWorkflowError(ValueError):
    pass


def transition_operation_plan_status(current_status: str, action: str, user_role: str) -> str:
    if action == "submit":
        if current_status not in {"draft", "rejected"}:
            raise OperationPlanWorkflowError("승인 요청이 불가한 상태입니다")
        return "pending_approval"

    if action == "approve":
        if user_role not in APPROVAL_ROLES:
            raise OperationPlanWorkflowError("승인 권한이 없습니다")
        if current_status != "pending_approval":
            raise OperationPlanWorkflowError("승인 대기 상태가 아닙니다")
        return "approved"

    if action == "reject":
        if user_role not in APPROVAL_ROLES:
            raise OperationPlanWorkflowError("반려 권한이 없습니다")
        if current_status != "pending_approval":
            raise OperationPlanWorkflowError("승인 대기 상태가 아닙니다")
        return "rejected"

    raise OperationPlanWorkflowError("지원하지 않는 운영계획 액션입니다")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

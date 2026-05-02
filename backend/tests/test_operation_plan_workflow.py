import unittest

from services.operation_plan_service import (
    OperationPlanWorkflowError,
    transition_operation_plan_status,
)


class OperationPlanWorkflowTest(unittest.TestCase):
    def test_submit_moves_draft_or_rejected_to_pending_approval(self):
        self.assertEqual(transition_operation_plan_status("draft", "submit", "member"), "pending_approval")
        self.assertEqual(transition_operation_plan_status("rejected", "submit", "member"), "pending_approval")

    def test_approve_requires_admin_or_approver_role(self):
        with self.assertRaises(OperationPlanWorkflowError):
            transition_operation_plan_status("pending_approval", "approve", "member")

        self.assertEqual(transition_operation_plan_status("pending_approval", "approve", "admin"), "approved")
        self.assertEqual(transition_operation_plan_status("pending_approval", "approve", "approver"), "approved")

    def test_reject_requires_pending_approval_and_approval_role(self):
        with self.assertRaises(OperationPlanWorkflowError):
            transition_operation_plan_status("draft", "reject", "admin")
        with self.assertRaises(OperationPlanWorkflowError):
            transition_operation_plan_status("pending_approval", "reject", "member")

        self.assertEqual(transition_operation_plan_status("pending_approval", "reject", "approver"), "rejected")


if __name__ == "__main__":
    unittest.main()

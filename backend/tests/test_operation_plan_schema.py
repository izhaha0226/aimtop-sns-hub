import unittest
import uuid

from schemas.operation_plan import OperationPlanUpdate


class OperationPlanSchemaTest(unittest.TestCase):
    def test_update_accepts_client_id_for_recovering_saved_plan_before_draft_generation(self):
        client_id = uuid.uuid4()

        update = OperationPlanUpdate(client_id=client_id)

        self.assertEqual(update.client_id, client_id)
        self.assertEqual(update.model_dump(exclude_none=True), {"client_id": client_id})


if __name__ == "__main__":
    unittest.main()

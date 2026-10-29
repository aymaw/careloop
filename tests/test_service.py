import tempfile
import unittest
from pathlib import Path

from careloop.cli import demo, seed
from careloop.service import CareLoop, Conflict, InvalidTransition

AT = "2030-01-02T10:00:00Z"


class CareLoopTests(unittest.TestCase):
    def setUp(self):
        self.app = CareLoop()
        seed(self.app)
        self.addCleanup(self.app.close)

    def route(self, referral="DEMO-001"):
        return self.app.approve(self.app.propose(referral), "reviewer", AT, referral + "-route")

    def test_demo_closes_only_completed_referral(self):
        result = demo()
        self.assertTrue(result["audit_verified"])
        self.assertEqual(result["referrals"][0]["status"], "closed")
        self.assertEqual(len(result["audit"]), 8)
        self.assertTrue(all(x["status"] == "draft" for x in result["outbox"]))

    def test_routing_is_proposal_until_approved(self):
        proposal = self.app.propose("DEMO-001")
        self.assertEqual(self.app.get("DEMO-001")["status"], "new")
        self.assertEqual(self.app.providers()[0]["slots"], 2)
        result = self.app.approve(proposal, "reviewer", AT, "once")
        self.assertEqual(result["status"], "routed")
        self.assertEqual(self.app.providers()[0]["slots"], 1)

    def test_version_prevents_stale_approval(self):
        proposal = self.app.propose("DEMO-001")
        self.route()
        with self.assertRaises(Conflict):
            self.app.approve(proposal, "reviewer", AT, "other")

    def test_tampered_proposal_is_rejected(self):
        proposal = self.app.propose("DEMO-001")
        proposal["provider"] = "demo-orbit"
        with self.assertRaises(ValueError):
            self.app.approve(proposal, "reviewer", AT, "bad")

    def test_capacity_changed_between_proposals(self):
        self.app.create("DEMO-004", "imaging", "north", "owner", "2030-01-01T09:00:00Z")
        one, two = self.app.propose("DEMO-002"), self.app.propose("DEMO-004")
        self.app.approve(one, "reviewer", AT, "one")
        with self.assertRaises(Conflict):
            self.app.approve(two, "reviewer", AT, "two")
        self.assertEqual(self.app.get("DEMO-004")["version"], 0)
        self.assertTrue(self.app.verify_audit("DEMO-004"))

    def test_idempotent_command_and_conflict(self):
        proposal = self.app.propose("DEMO-001")
        first = self.app.approve(proposal, "reviewer", AT, "once")
        self.assertEqual(first, self.app.approve(proposal, "reviewer", AT, "once"))
        with self.assertRaises(Conflict):
            self.app.approve(proposal, "someone-else", AT, "once")
        self.assertEqual(len(self.app.export()["outbox"]), 1)

    def test_illegal_transition_and_cross_referral_receipt(self):
        with self.assertRaises(InvalidTransition):
            self.app.command(
                "DEMO-001", "close", {"receipt": "missing"}, 0, "reviewer", AT, "close"
            )
        self.route()
        self.app.command("DEMO-001", "accept", {}, 1, "owner", AT, "accept")
        self.app.command(
            "DEMO-001", "schedule", {"slot": "2030-01-03T09:00:00Z"}, 2, "owner", AT, "schedule"
        )
        with self.assertRaises(InvalidTransition):
            self.app.command(
                "DEMO-001",
                "complete",
                {"receipt": "DEMO-RECEIPT-A"},
                3,
                "owner",
                AT,
                "early-complete",
            )
        completed_at = "2030-01-03T10:00:00Z"
        self.app.command(
            "DEMO-001",
            "complete",
            {"receipt": "DEMO-RECEIPT-A"},
            3,
            "owner",
            completed_at,
            "complete",
        )
        with self.assertRaises(InvalidTransition):
            self.app.command(
                "DEMO-001",
                "close",
                {"receipt": "DEMO-RECEIPT-B"},
                4,
                "owner",
                completed_at,
                "close",
            )
        self.assertEqual(self.app.get("DEMO-001")["status"], "completed")

    def test_decline_releases_capacity(self):
        self.route()
        item = self.app.command("DEMO-001", "decline", {}, 1, "reviewer", AT, "decline")
        self.assertIsNone(item["provider"])
        self.assertEqual(self.app.providers()[0]["slots"], 2)

    def test_no_capacity_and_model_allowlist(self):
        self.assertEqual(self.app.propose("DEMO-003")["action"], "needs_review")

        class BadPlanner:
            def json(self, *args):
                return {"provider": "external-hospital"}

        with self.assertRaises(ValueError):
            self.app.propose("DEMO-001", BadPlanner())

    def test_audit_detects_tampering(self):
        self.route()
        self.assertTrue(self.app.verify_audit("DEMO-001"))
        self.app.db.execute(
            "UPDATE audit SET actor='tampered' WHERE referral='DEMO-001' AND version=1"
        )
        self.assertFalse(self.app.verify_audit("DEMO-001"))

    def test_invalid_time_and_unknown_identifiers(self):
        with self.assertRaises(ValueError):
            self.app.create("DEMO-004", "rehab", "north", "owner", "2030-01-01")
        with self.assertRaises(KeyError):
            self.app.get("missing")
        with self.assertRaises(ValueError):
            self.app.add_provider("real-provider", "rehab", "north", 1)
        self.route()
        with self.assertRaises(ValueError):
            self.app.command(
                "DEMO-001", "accept", {}, 1, "reviewer", "2029-01-01T00:00:00Z", "backwards"
            )

    def test_worklist_excludes_closed_and_marks_overdue(self):
        items = self.app.worklist("2030-01-04T12:00:00Z")
        self.assertEqual(len(items), 3)
        self.assertTrue(all(i["overdue"] for i in items))

    def test_persistent_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "careloop.sqlite")
            first = CareLoop(path)
            seed(first)
            first.approve(first.propose("DEMO-001"), "reviewer", AT, "route")
            first.close()
            second = CareLoop(path)
            try:
                self.assertEqual(second.get("DEMO-001")["status"], "routed")
                self.assertTrue(second.verify_audit("DEMO-001"))
            finally:
                second.close()


if __name__ == "__main__":
    unittest.main()

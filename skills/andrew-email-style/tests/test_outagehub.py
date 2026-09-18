import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from outagehub import score_integration, validate_integration, cluster_accounts, WEIGHTS


class OutageHubTests(unittest.TestCase):
    def profile(self):
        keys = ("relevant_product", "existing_workflow", "insertion_point", "beneficiary", "customer_benefit", "canadian_relevance", "buy_vs_build", "buyer_function", "integration_sentence", "use_case_cluster", "next_question")
        return {**{k: "Sourced workflow" for k in keys}, "basis": ["workflow"], "product": "API", "gap_status": "unknown"}

    def test_distribution_counts_more_than_integration_ease(self):
        a = {"rating": 5, "reason": "Evidence of a platform", "basis": ["workflow"]}
        self.assertGreater(score_integration({"distribution_leverage": a}, ["workflow"])["weighted_priority"], score_integration({"ease_of_integration": a}, ["workflow"])["weighted_priority"])
        self.assertEqual(score_integration({}, ["workflow"])["unknown_dimensions"], list(WEIGHTS))
        with self.assertRaises(ValueError): score_integration({"distribution_leverage": a}, [])

    def test_unknown_supplier_allows_discovery_only(self):
        brief = {"qualification_scope": "workflow_discovery", "recommended_motion": {"stage": "workflow_conversation"}, "outagehub_integration": self.profile(), "grid_data_gap": {"equivalent_internal_visibility": None}}
        validate_integration(brief, {"workflow"})
        brief["recommended_motion"]["stage"] = "pilot"
        with self.assertRaises(ValueError): validate_integration(brief, {"workflow"})
        brief["recommended_motion"]["stage"] = "workflow_conversation"
        brief["grid_data_gap"]["equivalent_internal_visibility"] = True
        with self.assertRaises(ValueError): validate_integration(brief, {"workflow"})

    def test_cluster_deduplicates_buying_group(self):
        rows = [{"company": {"id": str(i), "name": str(i), "pause_group": "one-buyer"}, "outagehub_integration": self.profile(), "qualification": {"verdict": "yes"}} for i in range(2)]
        self.assertEqual(cluster_accounts(rows)[0]["count"], 1)

    def test_screen_target_does_not_require_qualifying_rejected_accounts(self):
        from unittest.mock import patch
        from mission import next_actions
        data={"engine":"outagehub_api","mission":{"target_accounts":3,"screen_target_accounts":3},"accounts":[{"qualification":{"verdict":"maybe"},"contacts":[]} for _ in range(3)],"counts":{"drafts":0},"limitations":[]}
        with patch('mission.review_campaign', return_value=data):
            self.assertFalse(any(t['step']=='discover_accounts' for t in next_actions(Path('/unused'))['tasks']))
            data['accounts'].pop()
            self.assertEqual(next_actions(Path('/unused'))['tasks'][0]['remaining'],1)


if __name__ == "__main__": unittest.main()

import copy
import json
import mailbox
from email.message import EmailMessage
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from history import save_thread, retrieve, records, infer_outcome, original_body
from research import add_source, campaign, read_sources, save_account, writer_packet
from ingest import ingest_mbox
from evaluate import rank
from sender import select_sender_context


def thread(body="Yep, absolutely.", kind="human", response="Yes 2 PM on Wednesday works."):
    return {"id": "thread-test", "account": "gordienko.adg@gmail.com", "source": "https://mail.google.com/test", "observed_at": "2026-09-14", "complete": True,
            "messages": [{"id": "sent-1", "kind": "sent", "sender": "gordienko.adg@gmail.com", "recipients": ["person@example.test"], "body": body, "context": {"relationship": "existing", "objective": "schedule"}},
                         {"id": "reply-1", "kind": kind, "sender": "person@example.test", "recipients": ["gordienko.adg@gmail.com"], "body": response}]}


def brief():
    return {"company": {"id": "test-co", "name": "Test Company", "fact_ids": ["f1"]},
            "facts": [{"id": "f1", "entity_id": "test-co", "text": "Test Company has a sorting robot.", "evidence": [{"source_id": "s1", "quote": "Test Company has a sorting robot."}]},
                      {"id": "f2", "entity_id": "kim", "text": "Kim manages automation.", "evidence": [{"source_id": "s1", "quote": "Kim manages automation."}]}],
            "hypotheses": [{"statement": "Variable inputs may make recovery worth investigating.", "confidence": "low", "basis": ["f1"]}],
            "qualification": {"verdict": "yes", "reason": "Sourced robotic process fits the research request.", "basis": ["f1"]},
            "stakeholders": [{"id": "kim", "name": "Kim", "role": "Automation Manager", "rank": 1, "reason": "Owns the process", "fact_ids": ["f2"]}],
            "recommended_motion": {"stage": "research_visit", "ask": "Understand one cell's intervention workflow", "interest_basis": []},
            "message_strategy": {"central_reason": "Investigate whether recovery could help", "problem_altitude": "workflow", "expose_facts": ["f1"], "why_now": None}}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sent_is_voice_without_approval_or_authorship_labels(self):
        save_thread(thread(), self.root)
        query = {"recipient": "person@example.test", "relationship": "existing", "objective": "schedule"}
        result = retrieve(query, self.root)
        self.assertEqual(result["voice_examples"][0]["body"], "Yep, absolutely.")
        self.assertNotIn("outcome", result["voice_examples"][0])
        self.assertEqual(len(result["response_examples"]), 1)
        modified = thread(kind="automatic")
        save_thread(modified, self.root)
        again = retrieve(query, self.root)
        self.assertEqual(result["voice_examples"], again["voice_examples"])
        self.assertEqual(again["response_examples"], [])

    def test_exact_person_can_override_other_objective_but_outcomes_must_match(self):
        save_thread(thread(), self.root)
        r = retrieve({"recipient": "person@example.test", "relationship": "cold", "objective": "research_visit"}, self.root)
        self.assertEqual(len(r["voice_examples"]), 1)
        self.assertEqual(r["response_examples"], [])

    def test_no_reply_and_multiple_sends_are_not_failures_or_double_success(self):
        self.assertIsNone(infer_outcome({}, [])["replied"])
        t = thread(); t["messages"].insert(1, {**t["messages"][0], "id": "sent-2"})
        save_thread(t, self.root)
        r = records(self.root)
        self.assertEqual(r[0]["outcome"]["type"], "reply_attribution_uncertain")
        self.assertEqual(r[1]["outcome"]["type"], "meeting_confirmed")

    def test_outcome_annotation_cannot_cite_own_or_automatic_mail(self):
        t = thread(kind="automatic")
        t["messages"][0]["annotations"] = {"outcome": {"value": {"type": "meeting_proposed"}, "confidence": "high", "evidence": [{"message_id": "reply-1", "quote": t["messages"][1]["body"]}]}}
        with self.assertRaises(ValueError):
            save_thread(t, self.root)

    def test_mbox_preserves_short_mail_and_does_not_merge_generic_subjects(self):
        box = mailbox.mbox(self.root / "test.mbox")
        for number in (1, 2):
            msg = EmailMessage(); msg["From"] = "gordienko.adg@gmail.com"
            msg["To"] = f'"Last, First" <person{number}@example.test>'
            msg["Subject"] = "Quick question"; msg["Message-ID"] = f"<test-{number}>"
            msg.set_content("Yep; that works.\n\nBest,\nAndrew")
            box.add(msg)
        box.flush(); box.close()
        result = ingest_mbox(self.root / "test.mbox", "gordienko.adg@gmail.com", self.root / "data")
        self.assertEqual(result["threads_saved"], 2)
        rs = records(self.root / "data")
        self.assertEqual(len(rs), 2)
        self.assertEqual(rs[0]["recipient"], ["person1@example.test"] if rs[0]["id"] == "<test-1>" else ["person2@example.test"])
        self.assertIn("Yep; that works.\n\nBest,", rs[0]["body"])

    def test_source_unicode_line_separators_round_trip(self):
        p = campaign("unicode-source", "test", self.root)
        text = "First paragraph\u2028Second paragraph\u2029Third paragraph\u0085End"
        source = {"id": "unicode", "url": "https://example.test", "observed_at": "2026-09-14", "tool": "test_fixture", "tool_ref": "unicode", "text": text}
        add_source(p, source)
        self.assertEqual(read_sources(p)["unicode"]["text"], text)
        add_source(p, source)
        self.assertEqual(len(read_sources(p)), 1)

    def sources(self):
        p = campaign("test", "A test only", self.root)
        add_source(p, {"id": "s1", "url": "https://example.test", "observed_at": "2026-09-14", "tool": "test_fixture", "tool_ref": "test-1", "text": "Test Company has a sorting robot. Kim manages automation."})
        return p

    def test_source_boundary_and_qualification(self):
        p = self.sources(); b = brief()
        path = save_account(p, b)
        self.assertTrue((path / "research.json").exists())
        packet = writer_packet(b, read_sources(p), "kim")
        self.assertEqual(len(packet["facts"]), 1)
        self.assertNotIn("text", packet["company"])
        bad = copy.deepcopy(b); bad["facts"][0]["evidence"][0]["quote"] = "Their cells keep failing"
        with self.assertRaises(ValueError): save_account(p, bad)
        bad = copy.deepcopy(b); bad["qualification"]["verdict"] = "maybe"
        with self.assertRaises(ValueError): writer_packet(bad, read_sources(p), "kim")
        bad = copy.deepcopy(b); bad["message_strategy"]["expose_facts"] = ["f1", "f2", "f1"]
        with self.assertRaises(ValueError): writer_packet(bad, read_sources(p), "kim")
        bad = copy.deepcopy(b); bad["recommended_motion"]["stage"] = "pilot"
        with self.assertRaises(ValueError): save_account(p, bad)

    def test_source_ids_immutable_and_unknown_contacts_rejected(self):
        p = self.sources(); s = read_sources(p)["s1"]
        add_source(p, s)
        self.assertEqual(len(read_sources(p)), 1)
        with self.assertRaises(ValueError): add_source(p, {**s, "text": "Something else"})
        with self.assertRaises(ValueError): writer_packet(brief(), read_sources(p), "invented-person")

    def test_impact_motivation_stays_an_inference_with_sourced_basis(self):
        p = self.sources(); b = brief(); sources = read_sources(p)
        self.assertIsNone(writer_packet(b, sources, "kim")["motivation"])
        motivation = {"societal_outcome": "Less material wasted during sorting",
                      "technical_problem": "Investigate recovery when inputs vary",
                      "andrew_connection": "Andrew wants to apply his recovery work to useful problems",
                      "kind": "inference", "basis": ["f1"]}
        b["message_strategy"]["motivation"] = motivation
        packet = writer_packet(b, sources, "kim")
        self.assertEqual(packet["motivation"], motivation)
        self.assertEqual(len(packet["facts"]), 1)
        for change in ({"basis": ["invented"]}, {"kind": "fact"}, {"andrew_connection": ""}):
            bad = copy.deepcopy(b); bad["message_strategy"]["motivation"].update(change)
            with self.assertRaises(ValueError): writer_packet(bad, sources, "kim")

    def test_critic_and_style_gate_cannot_be_outweighed(self):
        candidates = [{"id": "ok", "body": "That's totally okay; video this week works great for me."}, {"id": "bad", "body": "That's okay—video works."}]
        c = {k: True for k in ("facts_supported", "thought_preserved", "plain_language_preserved", "research_quiet", "stage_correct", "phrase_flags_reviewed")}
        c.update(voice_fit=4, recipient_fit=4, ai_sentence=None)
        critics = {"ok": c, "bad": {**c, "voice_fit": 5}}
        result = rank(candidates, {}, critics)
        self.assertEqual(result["winner"], "ok")
        self.assertFalse(result["candidates"][1]["eligible"])
        self.assertIsNone(rank(candidates, {}, {})["winner"])
        self.assertIsNone(rank([candidates[0]], {}, {"ok": {**c, "facts_supported": False, "voice_fit": 5}})["winner"])

    def test_cleaner_preserves_cadence_and_strips_clear_quote(self):
        self.assertEqual(original_body("Yep; absolutely.\n\n\nBest,\nAndrew\n\nOn Tuesday Someone wrote:\n> old"), "Yep; absolutely.\n\n\nBest,\nAndrew")

    def test_task_seed_outranks_history_without_becoming_sent_or_outcome_evidence(self):
        save_thread(thread(), self.root)
        supplied = {"body": "I build systems that search for failures and recovery paths.", "source": "current user draft"}
        existing = {"body": "An earlier task-specific email.", "source": "local draft"}
        query = {"recipient": "person@example.test", "relationship": "existing", "objective": "schedule"}
        before = retrieve(query, self.root)
        result = retrieve({**query, "supplied_draft": supplied, "existing_task_draft": existing}, self.root)
        self.assertEqual(result["task_draft"]["body"], supplied["body"])
        for key in ("voice_examples", "response_examples", "recipient_history", "coverage"):
            self.assertEqual(result[key], before[key])
        fallback = retrieve({**query, "existing_task_draft": existing}, self.root)
        self.assertEqual(fallback["task_draft"]["body"], existing["body"])
        with self.assertRaises(ValueError):
            retrieve({**query, "supplied_draft": {"body": "Missing provenance"}}, self.root)

    def test_high_voice_score_cannot_override_lost_task_specific_detail(self):
        seed = {"body": "I build systems that search for failures and recovery paths.", "source": "current user draft"}
        candidates = [{"id": "kept", "body": seed["body"]}, {"id": "flattened", "body": "My background is in AI."}]
        c = {k: True for k in ("facts_supported", "thought_preserved", "plain_language_preserved", "research_quiet", "stage_correct", "phrase_flags_reviewed", "task_draft_preserved", "technical_detail_preserved")}
        c.update(voice_fit=4, recipient_fit=4, ai_sentence=None)
        critics = {"kept": c, "flattened": {**c, "voice_fit": 5, "technical_detail_preserved": False}}
        for retrieval, packet in (({"task_draft": seed}, None), ({}, {"task_draft": seed})):
            result = rank(candidates, retrieval, critics, packet)
            self.assertEqual(result["winner"], "kept")
            self.assertIn("technical_detail_preserved", result["candidates"][1]["rejection_reasons"])
        missing = {k: v for k, v in c.items() if k != "task_draft_preserved"}
        self.assertIsNone(rank([candidates[0]], {"task_draft": seed}, {"kept": missing})["winner"])

    def test_sender_role_depends_on_objective_without_inventing_identity(self):
        for context, expected in [
            ({"objective": "technical_contract"}, "technical_contract"),
            ({"objective": "pilot", "project": "Wapahki"}, "wapahki_pilot"),
            ({"objective": "investor", "project": "Wapahki"}, "wapahki_investor"),
            ({"objective": "research_visit", "project": "Wapahki"}, "factory_learning"),
            ({"objective": "acquisition", "project": "OutageHub"}, "outagehub_acquisition"),
            ({"objective": "api_sales", "project": "OutageHub"}, "outagehub_api"),
            ({"objective": "personal_reconnection", "project": "Wapahki"}, "warm_personal"),
            ({"recipient": "A CEO", "relationship": "warm"}, "unknown"),
        ]:
            with self.subTest(context=context):
                selected = select_sender_context(context)
                self.assertEqual(selected["mode"], expected)
                self.assertEqual(selected["identity"], [])
        context = {"objective": "technical_contract", "current_facts": ["Current research work", "Unrelated acquisition discussion"], "sender_fact_indices": [0]}
        self.assertEqual(select_sender_context(context)["identity"], [{"text": "Current research work", "source": "current_facts[0]"}])
        for invalid in ([-1], [2], [0, 0], [True]):
            with self.assertRaises(ValueError):
                select_sender_context({**context, "sender_fact_indices": invalid})

    def test_sender_fit_is_required_when_context_is_present(self):
        candidates = [{"id": "draft", "body": "Happy to discuss the outage data."}]
        c = {k: True for k in ("facts_supported", "thought_preserved", "plain_language_preserved", "research_quiet", "stage_correct", "phrase_flags_reviewed")}
        c.update(voice_fit=5, recipient_fit=5)
        retrieval = {"sender_context": select_sender_context({"project": "OutageHub", "objective": "api_sales"})}
        self.assertIsNone(rank(candidates, retrieval, {"draft": c})["winner"])
        self.assertEqual(rank(candidates, retrieval, {"draft": {**c, "sender_context_fit": True}})["winner"], "draft")


if __name__ == "__main__":
    unittest.main()

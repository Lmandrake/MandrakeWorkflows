"""The example's scorer. Every wrong answer here passed the first, substring-only version
(adversarial review, 2026-10-26); every right one must keep passing."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
import eval_qa  # noqa: E402

Q = {q["id"]: q for q in json.loads((ROOT / "examples" / "questions.json").read_text())["questions"]}

WRONG = {
    "q04": "Cedar Ridge had 15 faulty controllers.",
    "q10": "Cedar Ridge, week 17, 19 alerts.",
    "q11": "1291 cubic metres.",
    "q12": "Dunmore did best because it had a thousand controllers.",
    "q13": "A correction was applied; rainfall was not comparable (18%).",
    "q01": "not in the folder (23.1 was a guess)",
    "q13 ": "Yes, a correction was applied for 8% more rain.",
}
RIGHT = {
    "q04": "5 controllers, at Cedar Ridge",
    "q10": "Cedar Ridge, week 7, with 9 alerts",
    "q11": "291 m3",
    "q12": "Its plots are on sandy soil, which fixed timers over-watered most.",
    "q13": "No; rainfall was within 8% of the 2025 season at every site.",
    "q13 ": "No weather correction was applied because rainfall was within 8% of 2025",
    "q05": "Firmware 2.3.4, installed on 18 August 2026",
    "q07": "$61,400",
    "q02": "Dunmore, 27.2%",
}


class Scorer(unittest.TestCase):
    def test_wrong_answers_fail(self):
        for qid, answer in WRONG.items():
            self.assertEqual(eval_qa.score(Q[qid.strip()], answer), 0, f"{qid}: {answer!r}")

    def test_right_answers_pass(self):
        for qid, answer in RIGHT.items():
            self.assertEqual(eval_qa.score(Q[qid.strip()], answer), 1, f"{qid}: {answer!r}")

    def test_every_question_has_a_check(self):
        for q in Q.values():
            self.assertTrue(q["checks"], q["id"])


if __name__ == "__main__":
    unittest.main()

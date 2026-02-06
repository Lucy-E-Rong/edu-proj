from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def _example_records() -> List[Dict]:
    return [
        {
            "messages": [
                {"role": "user", "content": "Create one multiple-choice question about phishing detection."},
                {
                    "role": "assistant",
                    "content": "Question: Which sign most strongly suggests a phishing email?\nA. Personalized greeting\nB. Urgent request to reset credentials through a mismatched link\nC. Company logo\nD. Normal sender domain\nAnswer: B\nExplanation: Mismatched links plus urgency are high-risk phishing indicators.",
                },
            ]
        },
        {
            "messages": [
                {"role": "user", "content": "Write a short-answer exercise on least privilege for first-year students."},
                {
                    "role": "assistant",
                    "content": "Prompt: Explain least privilege in 3-4 sentences and give one workplace example.\nSample key points: users should have only permissions needed for assigned tasks; reduces blast radius; periodic access review prevents privilege creep.",
                },
            ]
        },
        {
            "messages": [
                {"role": "user", "content": "Design a scenario question about incident response after ransomware detection."},
                {
                    "role": "assistant",
                    "content": "Scenario: A finance workstation reports mass file encryption and ransom notes.\nTask: List the first five response actions in order.\nReference response: isolate host, notify IR lead, preserve volatile evidence, scope affected systems, initiate communication protocol.",
                },
            ]
        },
        {
            "messages": [
                {"role": "user", "content": "Generate an MCQ on password policy."},
                {
                    "role": "assistant",
                    "content": "Question: Which policy most improves password security?\nA. Reuse allowed\nB. Minimum 6 chars\nC. MFA + long passphrases\nD. Shared team accounts\nAnswer: C",
                },
            ]
        },
        {
            "messages": [
                {"role": "user", "content": "Create a rubric for evaluating a threat-modeling diagram."},
                {
                    "role": "assistant",
                    "content": "Rubric (10 points): assets identified (2), trust boundaries marked (2), attack paths reasoned (2), mitigations mapped (2), clarity and terminology (2).",
                },
            ]
        },
    ]


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    rows = _example_records()
    train_rows = rows[:4]
    eval_rows = rows[4:]

    write_jsonl(Path("data/processed/train.jsonl"), train_rows)
    write_jsonl(Path("data/processed/eval.jsonl"), eval_rows)
    print("Wrote data/processed/train.jsonl and data/processed/eval.jsonl")


if __name__ == "__main__":
    main()

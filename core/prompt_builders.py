from __future__ import annotations

from typing import Iterable, List, Mapping


def build_cag_prompt(style_guide: str, example: str, user_prompt: str) -> str:
    return (
        "[STYLE GUIDE]\n"
        f"{style_guide.strip()}\n\n"
        "[EXAMPLE]\n"
        f"{example.strip()}\n\n"
        "[USER PROMPT]\n"
        f"{user_prompt.strip()}"
    )


def build_rag_prompt(
    retrieved_context: Iterable[Mapping[str, str]],
    conversation_history: List[Mapping[str, str]],
    question: str,
) -> str:
    context_lines = []
    for idx, chunk in enumerate(retrieved_context, start=1):
        source = chunk.get("source", "unknown")
        chunk_id = chunk.get("chunk_id", "n/a")
        text = chunk.get("text", "")
        context_lines.append(f"({idx}) source={source}, chunk_id={chunk_id}\n{text}")

    history_lines = []
    for item in conversation_history:
        role = item.get("role", "unknown")
        content = item.get("content", "")
        history_lines.append(f"{role}: {content}")

    context_block = "\n\n".join(context_lines) if context_lines else "No retrieved context."
    history_block = "\n".join(history_lines) if history_lines else "No conversation history."

    return (
        "[RETRIEVED CONTEXT]\n"
        f"{context_block}\n\n"
        "[CONVERSATION HISTORY]\n"
        f"{history_block}\n\n"
        "[QUESTION]\n"
        f"{question.strip()}"
    )

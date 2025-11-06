"""Generate node: final answer generation using LLM."""

from collections import Counter
from typing import Callable, Dict, Any, List
from langchain.schema import Document


def _format_documents(documents: List[Document]) -> str:
    """Format documents for context."""
    if not documents:
        return "관련 문서를 찾지 못했습니다."

    formatted = []
    for i, doc in enumerate(documents, 1):
        metadata = doc.metadata
        source = f"문서 {i}"

        # Extract source info from metadata
        if metadata.get("job_title"):
            source = f"{metadata['job_title']}"
        if metadata.get("organization"):
            source += f" - {metadata['organization']}"
        if metadata.get("source"):
            source = metadata["source"]

        formatted.append(f"[{source}]\n{doc.page_content}\n")

    return "\n".join(formatted)


def make_generate_node(hooks: Any) -> Callable:
    """Factory: create generate node with category-specific prompt.

    Args:
        hooks: CategoryHooks instance with answer_system_prompt

    Returns:
        Node function: state -> updated state
    """

    def generate_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final answer using retrieved documents.

        Args:
            state: Agent state dict

        Returns:
            Updated state with answer and sources
        """
        query = state.get("query", "")
        documents = state.get("documents", [])
        web_documents = state.get("web_documents", [])

        # Combine all documents
        all_docs = documents + web_documents

        # Use category-specific system prompt
        system_prompt = hooks.answer_system_prompt

        # Format context
        context = _format_documents(all_docs)

        try:
            # Use cached LLM instance from hooks
            llm = hooks.llm

            messages = [{"role": "system", "content": system_prompt}]

            # history = state.get("history") or []
            # if history:
            #     history_lines = []
            #     for turn in history[-8:]:
            #         role = (
            #             turn.get("role")
            #             if isinstance(turn, dict)
            #             else getattr(turn, "role", None)
            #         )
            #         content = (
            #             turn.get("content")
            #             if isinstance(turn, dict)
            #             else getattr(turn, "content", None)
            #         )
            #         if not content:
            #             continue
            #         label = "사용자" if role == "user" else "상담사"
            #         history_lines.append(f"{label}: {content}")
            #     if history_lines:
            #         messages.append(
            #             {
            #                 "role": "system",
            #                 "content": "이전 대화 이력:\n" + "\n".join(history_lines),
            #             }
            #         )

            user_prompt = (
                f"최신 사용자 질문: {query}\n\n"
                f"참고 문서:\n{context}\n\n"
                "지금까지의 문맥을 바탕으로 답변을 작성해줘."
            )

            messages.append({"role": "user", "content": user_prompt})

            response = llm.invoke(messages)
            answer = response.content.strip()

            trace = state.get("retrieval_trace", [])
            origin_counts = Counter(
                (doc.metadata.get("origin") or "vector_db") for doc in all_docs
            )

            # summary_lines = []
            # if origin_counts:
            #     vector_count = origin_counts.get("vector_db")
            #     web_count = origin_counts.get("web_search")
            #     if vector_count:
            #         summary_lines.append(f"벡터 DB 문서 {vector_count}건")
            #     if web_count:
            #         summary_lines.append(f"웹 검색 문서 {web_count}건")
            # if not summary_lines:
            #     summary_lines.append("참고 문서를 찾지 못했습니다")

            # summary_block = "\n".join(f"- {line}" for line in summary_lines)
            # answer_with_summary = f"{answer}\n\n---\n**출처 요약**\n{summary_block}"

            answer_with_summary = f"{answer}"

            # Extract sources
            sources = [
                {
                    "content": doc.page_content[:200],
                    "metadata": dict(doc.metadata),
                }
                for doc in all_docs[:5]
            ]

            retrieval_stats = {
                "origin_counts": dict(origin_counts),
                "trace": trace,
            }

            return {
                "answer": answer_with_summary,
                "sources": sources,
                "retrieval_stats": retrieval_stats,
            }

        except Exception as e:
            print(f"[ERROR] Generation failed: {e}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "sources": [],
            }

    return generate_node


__all__ = ["make_generate_node"]

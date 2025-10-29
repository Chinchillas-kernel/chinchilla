"""Grade node: evaluate document relevance to query."""
from typing import Callable, Dict, Any, Literal
from langchain_upstage import ChatUpstage
from app.config import settings


def make_grade_node(hooks: Any) -> Callable:
    """Factory: create grade node to evaluate document relevance.

    Args:
        hooks: CategoryHooks instance

    Returns:
        Node function: state -> routing decision ("yes" or "no")
    """

    def grade_node(state: Dict[str, Any]) -> Literal["yes", "no"]:
        """Grade retrieved documents for relevance.

        Args:
            state: Agent state dict

        Returns:
            "yes" if documents are relevant, "no" if need to rewrite query
        """
        query = state.get("query", "")
        rewritten_query = state.get("rewritten_query", query)
        documents = state.get("documents", [])

        # If no documents, definitely need to rewrite
        if not documents:
            print("[GRADE] No documents retrieved → rewrite")
            return "no"

        # Check relevance scores first (if available)
        relevant_docs = [
            doc
            for doc in documents
            if doc.metadata.get("relevance_score", 0) >= hooks.min_relevance_threshold
        ]

        if not relevant_docs:
            print(f"[GRADE] No documents above threshold ({hooks.min_relevance_threshold}) → rewrite")
            return "no"

        # Use LLM to grade relevance
        # Format documents for evaluation
        doc_texts = []
        for i, doc in enumerate(documents[:3], 1):  # Check top 3 docs
            doc_texts.append(f"문서 {i}:\n{doc.page_content[:300]}")

        context = "\n\n".join(doc_texts)

        grade_prompt = f"""다음 문서들이 사용자의 질문과 관련이 있는지 평가하세요.

사용자 질문: {rewritten_query}

검색된 문서:
{context}

문서가 질문에 답변하는데 도움이 되는 정보를 포함하고 있습니까?
관련이 있으면 "yes", 없으면 "no"만 답변하세요."""

        try:
            llm = ChatUpstage(
                api_key=settings.upstage_api_key,
                model="solar-pro",
            )

            messages = [
                {
                    "role": "system",
                    "content": "너는 문서 관련성 평가 전문가다. yes 또는 no로만 답변하라.",
                },
                {"role": "user", "content": grade_prompt},
            ]

            response = llm.invoke(messages)
            decision = response.content.strip().lower()

            # Parse decision
            if "yes" in decision:
                print("[GRADE] Documents are relevant → generate")
                return "yes"
            else:
                print("[GRADE] Documents not relevant → rewrite")
                return "no"

        except Exception as e:
            print(f"[WARN] Grade failed: {e}, defaulting to yes")
            # If grading fails, proceed with documents we have
            return "yes"

    return grade_node


__all__ = ["make_grade_node"]

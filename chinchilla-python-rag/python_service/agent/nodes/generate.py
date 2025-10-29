"""Generate node: final answer generation using LLM."""
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

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"질문: {query}\n\n참고 문서:\n{context}\n\n답변:",
                },
            ]

            response = llm.invoke(messages)
            answer = response.content.strip()

            # Extract sources
            sources = [
                {
                    "content": doc.page_content[:200],
                    "metadata": dict(doc.metadata),
                }
                for doc in all_docs[:5]
            ]

            return {"answer": answer, "sources": sources}

        except Exception as e:
            print(f"[ERROR] Generation failed: {e}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "sources": [],
            }

    return generate_node


__all__ = ["make_generate_node"]

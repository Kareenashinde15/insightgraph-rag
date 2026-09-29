import os
from typing import Any, Optional

import requests

from backend.app.llm.provider_base import BaseLLMProvider, LLMAnswerResponse


class GroqProvider(BaseLLMProvider):
    """Groq chat-completions adapter for the local hobby application."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    @staticmethod
    def _citations(retrieval_result: Any) -> list[dict[str, Any]]:
        citations = []
        for idx, chunk in enumerate(getattr(retrieval_result, "vector_chunks", []), 1):
            citations.append({
                "citation_index": idx,
                "document_id": chunk.document_id,
                "document_name": chunk.source or chunk.document_id,
                "page": chunk.page,
                "chunk_id": chunk.chunk_id,
                "snippet": chunk.text[:220] + "..." if len(chunk.text) > 220 else chunk.text,
                "similarity_score": chunk.similarity,
            })
        return citations

    def generate_answer(
        self,
        query: str,
        context: str,
        retrieval_result: Any,
        temperature: float = 0.2,
    ) -> LLMAnswerResponse:
        citations = self._citations(retrieval_result)
        if not self.api_key:
            return LLMAnswerResponse(
                answer="Groq is not configured. Add GROQ_API_KEY to the local environment to enable generated answers.",
                citations=citations,
                tokens_used=0,
                model=self.model,
                grounded=False,
                uncertainty_noted=True,
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Answer only from the evidence below. If the evidence is insufficient, say so. "
                        "Do not invent citations, entities, or relationships.\n\n"
                        f"Question: {query}\n\nEvidence:\n{context}"
                    ),
                },
            ],
            "temperature": temperature,
            "max_tokens": 1200,
        }

        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=(5, 60),
            )
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return LLMAnswerResponse(
                answer=answer,
                citations=citations,
                tokens_used=usage.get("total_tokens", 0),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                model=data.get("model", self.model),
                grounded=bool(citations or getattr(retrieval_result, "graph_facts", [])),
            )
        except requests.RequestException as exc:
            return LLMAnswerResponse(
                answer=f"Groq request failed: {exc.__class__.__name__}. Check the API key, model, network, or rate limits.",
                citations=citations,
                tokens_used=0,
                model=self.model,
                grounded=False,
                uncertainty_noted=True,
            )
        except (KeyError, IndexError, TypeError, ValueError):
            return LLMAnswerResponse(
                answer="Groq returned an unexpected response. No generated answer is available.",
                citations=citations,
                tokens_used=0,
                model=self.model,
                grounded=False,
                uncertainty_noted=True,
            )


def get_llm_provider(provider_name: str = "groq") -> BaseLLMProvider:
    # Keep the provider selection explicit even though Groq is the only supported
    # external provider for this local application.
    if provider_name.lower().strip() == "groq":
        return GroqProvider()
    raise ValueError(f"Unsupported LLM provider: {provider_name}")

# agent.py (Bản cập nhật)
from __future__ import annotations
import time
import asyncio # Thêm để hỗ trợ async
from dataclasses import dataclass
from . import metrics
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .tracing import langfuse_context, observe

@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float

class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(name="lab_agent_run") # Tên trace hiển thị trên Langfuse
    async def run(self, user_id: str, feature: str, session_id: str, message: str) -> AgentResult:
        started = time.perf_counter()
        
        # 1. RAG Retrieval (Giả định retrieve có thể tốn thời gian)
        docs = retrieve(message)
        
        # 2. Prompt Engineering nâng cao
        prompt = (
            f"System: You are a helpful assistant for {feature}.\n"
            f"Context: {docs}\n"
            f"User Question: {message}"
        )
        
        # 3. LLM Generation (Giả lập async call)
        # Trong thực tế bạn sẽ dùng: response = await self.llm.agenerate(prompt)
        response = self.llm.generate(prompt)
        
        # 4. Evaluation & Metrics
        quality_score = self._heuristic_quality(message, response.text, docs)
        latency_ms = int((time.perf_counter() - started) * 1000)
        cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

        # 5. Enrich Langfuse Trace
        langfuse_context.update_current_trace(
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
            metadata={"env": "production"} # Thêm metadata để lọc
        )
        
        langfuse_context.update_current_observation(
            input=prompt,
            output=response.text,
            metadata={"doc_count": len(docs), "quality_score": quality_score},
            usage_details={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
        )

        # 6. Record Internal Metrics
        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        # Giá giả định cho Claude 3.5 Sonnet
        input_cost = (tokens_in / 1_000_000) * 3.0
        output_cost = (tokens_out / 1_000_000) * 15.0
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        # Kiểm tra xem có tài liệu bổ trợ không
        if docs and "No domain document matched" not in docs[0]:
            score += 0.2
        # Kiểm tra độ dài câu trả lời
        if 50 < len(answer) < 500:
            score += 0.1
        # Kiểm tra mức độ liên quan cơ bản
        if any(word in answer.lower() for word in question.lower().split()[:3]):
            score += 0.2
        return round(max(0.0, min(1.0, score)), 2)
# scripts/test_legal_simple.py
import time
from agent.router_runtime import get_runtime
from agent.router import dispatch
from app.schemas import LegalRequest, LegalPayload, LegalProfile

print("에이전트 런타임 초기화 중...")
graphs, hooks = get_runtime()
print("런타임 준비 완료.")

req = LegalRequest(
    category="legal",
    payload=LegalPayload(
        query="내 자식이 3명인데 내 재산은 부동산이랑 주식이랑 현금 이렇게 있어 상속하려면 언제가 좋고 어떻게 해야할까",
        profile=LegalProfile(age=68, region="서울"),
    ),
)

print(f"\n[질문] {req.payload.query}\n" + "-" * 50)

# 시간 측정 시작
start_time = time.time()

# 에이전트 실행
response = dispatch(req, graphs=graphs, hooks=hooks)

# 시간 측정 종료
end_time = time.time()
duration = end_time - start_time

print("\n[답변]")
print(response.answer)

print("\n" + "-" * 50)
print(f"⏱️  답변 생성 시간: {duration:.2f}초")

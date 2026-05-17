"""Full pipeline integration test - Chinese inputs"""
import requests
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

tests = [
    ("你好呀", "casual_chat", "model_fast"),
    ("血压多少算正常", "health_qa", "model_fast"),
    ("我头疼两天了还有点恶心", "symptom_consult", "model_med"),
    ("布洛芬和阿莫西林能一起吃吗", "drug_consult", "model_med"),
    ("帮我看看这个体检报告，血糖7.2", "report_parse", "report_pipeline"),
    ("胸口突然剧烈疼痛喘不上气", "emergency", "emergency_handler"),
    ("提醒我明天早上8点吃降压药", "task_command", "agent_executor"),
]

print("=" * 70)
print("HealthMate Full Pipeline Test")
print("=" * 70)

passed = 0
for user_input, expected_intent, expected_route in tests:
    r = requests.post("http://localhost:8090/api/chat", params={"user_input": user_input})
    d = r.json()

    intent_ok = d["intent"] == expected_intent
    route_ok = d["model"] == expected_route

    status = "PASS" if (intent_ok and route_ok) else "FAIL"
    if status == "PASS":
        passed += 1

    print(f"\n[{status}] Input: {user_input}")
    print(f"  Intent:  {d['intent']:20s} (expected: {expected_intent})")
    print(f"  Route:   {d['model']:20s} (expected: {expected_route})")
    print(f"  Response: {d['response'][:80]}...")

print(f"\n{'=' * 70}")
print(f"Result: {passed}/{len(tests)} passed")
print(f"{'=' * 70}")

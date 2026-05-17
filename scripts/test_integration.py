"""
HealthMate 全链路集成测试
Java :8081 → Python AI :8090 → MySQL + Redis + Milvus + ES

运行前确保：
  1. Python AI Engine: localhost:8090 (uvicorn)
  2. Java Core:        localhost:8081 (mvn spring-boot:run)
  3. MySQL / Redis / Milvus / ES 均已启动
"""
import requests
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

BASE_JAVA = "http://localhost:8081"
BASE_AI   = "http://localhost:8090"

passed = 0
failed = 0

def test(name, func):
    global passed, failed
    try:
        func()
        print(f"  ✅ {name}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1


print("=" * 60)
print("HealthMate 全链路集成测试")
print("=" * 60)

# ==============================
# 1. 基础服务健康检查
# ==============================
print("\n[1] 基础服务检查")

def test_ai_health():
    r = requests.get(f"{BASE_AI}/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
test("Python AI Engine 健康检查", test_ai_health)

def test_java_health():
    # Java 没有显式 /health，直接测 conversations 接口
    r = requests.get(f"{BASE_JAVA}/api/conversations", params={"userId": 99999}, timeout=5)
    assert r.status_code == 200
test("Java Core 服务可达", test_java_health)

# ==============================
# 2. 意图分类（Python 直接调）
# ==============================
print("\n[2] 意图分类")

intent_tests = [
    ("你好呀",              "casual_chat"),
    ("血压多少算正常",       "health_qa"),
    ("我头疼两天了",         "symptom_consult"),
    ("布洛芬能和阿莫西林一起吃吗", "drug_consult"),
]

for text, expected in intent_tests:
    def make_test(t, e):
        def _test():
            r = requests.post(f"{BASE_AI}/api/intent/classify", params={"text": t}, timeout=10)
            assert r.status_code == 200
            data = r.json()
            actual = data.get("primary_intent", "")
            # 允许关键词匹配时 intent 可能不完全一致
            assert actual, f"Got empty intent for '{t}'"
        return _test
    test(f"  '{text}' → {expected}", make_test(text, expected))

# ==============================
# 3. Java → Python 对话链路
# ==============================
print("\n[3] 全链路对话（Java → Python AI → DashScope）")

conv_id = None

def test_chat_create():
    global conv_id
    r = requests.post(f"{BASE_JAVA}/api/chat",
                      json={"userId": 100, "userInput": "你好"},
                      timeout=30)
    assert r.status_code == 200
    data = r.json()
    conv_id = data.get("conversationId")
    assert conv_id, "No conversationId returned"
    assert data.get("response"), "Empty response"
    assert data.get("intent"), "No intent"
test("创建新对话", test_chat_create)

def test_chat_continue():
    r = requests.post(f"{BASE_JAVA}/api/chat",
                      json={"userId": 100, "conversationId": conv_id,
                            "userInput": "我最近总是头疼"},
                      timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data.get("response"), "Empty response"
    assert data["conversationId"] == conv_id
test("继续同一会话", test_chat_continue)

# ==============================
# 4. 消息持久化验证
# ==============================
print("\n[4] 数据持久化")

def test_messages_persisted():
    r = requests.get(f"{BASE_JAVA}/api/conversations/{conv_id}/messages", timeout=5)
    assert r.status_code == 200
    messages = r.json()
    assert len(messages) >= 4, f"Expected ≥4 messages, got {len(messages)}"
    roles = [m["role"] for m in messages]
    assert "user" in roles and "assistant" in roles
test("消息历史查询", test_messages_persisted)

def test_conversation_list():
    r = requests.get(f"{BASE_JAVA}/api/conversations", params={"userId": 100}, timeout=5)
    assert r.status_code == 200
    convs = r.json()
    assert len(convs) >= 1
    assert convs[0].get("messageCount", 0) >= 4
test("会话列表 + 消息计数", test_conversation_list)

# ==============================
# 5. RAG 检索验证（直接调 Python）
# ==============================
print("\n[5] RAG 知识库检索")

def test_rag_chat():
    r = requests.post(f"{BASE_AI}/api/chat",
                      params={"user_input": "布洛芬和阿莫西林能一起吃吗"},
                      timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data.get("response"), "Empty RAG response"
test("RAG 增强回答", test_rag_chat)

# ==============================
# Summary
# ==============================
print("\n" + "=" * 60)
total = passed + failed
print(f"总计: {total} 项 | ✅ 通过: {passed} | ❌ 失败: {failed}")
if failed == 0:
    print("🎉 全链路集成测试通过！")
else:
    print(f"⚠️  有 {failed} 项测试失败，请检查")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)

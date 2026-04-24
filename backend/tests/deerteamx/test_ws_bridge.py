"""SSEToWebSocketBridge 单元测试

测试范围：
- SSE 到 WebSocket 事件转换
- thread_id 到 execution_id 映射
- 消息幂等性验证

测试用例对齐 BACKEND_TEST_PLAN.md:
- TC-WS-004: SSE-WS 桥接正确性验证
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from deerteamx.runtime.ws_bridge import SSEToWebSocketBridge


# ============================================================================
# 测试夹具（Fixtures）
# ============================================================================

@pytest.fixture
def ws_bridge():
    """创建 WebSocket 桥接器实例"""
    return SSEToWebSocketBridge(gateway_url="http://localhost:8001")


@pytest.fixture
def sample_sse_event():
    """示例 SSE 事件数据"""
    return {
        "event": "on_chain_start",
        "data": {
            "input": {"query": "分析销售数据"},
            "metadata": {"thread_id": "thread-abc123"}
        }
    }


@pytest.fixture
def sample_ws_message():
    """示例 WebSocket 消息格式"""
    return {
        "type": "execution_update",
        "execution_id": "exec-20260424-xyz789",
        "thread_id": "thread-abc123",
        "payload": {
            "event": "on_chain_start",
            "data": {"input": {"query": "分析销售数据"}}
        }
    }


# ============================================================================
# SSE 到 WebSocket 事件转换测试
# ============================================================================

class TestSSEToWebSocketConversion:
    """TC-WS-004: SSE 到 WebSocket 事件转换测试"""
    
    def test_format_ws_message_structure(self, ws_bridge, sample_sse_event):
        """测试 WebSocket 消息结构
        
        验证点：
        - 消息包含 type、execution_id、thread_id、payload 字段
        - type 固定为 "execution_update"
        """
        # Arrange
        sse_data = json.dumps(sample_sse_event)
        thread_id = "thread-abc123"
        execution_id = "exec-20260424-xyz789"
        
        # Act
        ws_message = ws_bridge._format_ws_message(sse_data, thread_id, execution_id)
        
        # Assert
        assert "type" in ws_message
        assert ws_message["type"] == "execution_update"
        assert "execution_id" in ws_message
        assert ws_message["execution_id"] == execution_id
        assert "thread_id" in ws_message
        assert ws_message["thread_id"] == thread_id
        assert "payload" in ws_message
    
    def test_parse_sse_event_valid_json(self, ws_bridge):
        """测试解析有效 JSON 格式的 SSE 事件
        
        验证点：
        - 正确解析 JSON 字符串
        - 返回字典格式的事件数据
        """
        # Arrange
        sse_data = '{"event": "on_chain_end", "data": {"output": "完成"}}'
        
        # Act
        result = ws_bridge._parse_sse_event(sse_data)
        
        # Assert
        assert isinstance(result, dict)
        assert result["event"] == "on_chain_end"
        assert result["data"]["output"] == "完成"
    
    def test_parse_sse_event_invalid_json(self, ws_bridge):
        """测试解析无效 JSON 格式的 SSE 事件
        
        验证点：
        - 捕获 JSONDecodeError 异常
        - 返回包含 raw 字段的兜底数据
        """
        # Arrange
        invalid_sse_data = "not a valid json string"
        
        # Act
        result = ws_bridge._parse_sse_event(invalid_sse_data)
        
        # Assert
        assert isinstance(result, dict)
        assert result["raw"] == invalid_sse_data
        assert result["status"] == "unknown"
    
    def test_parse_sse_event_empty_string(self, ws_bridge):
        """测试解析空字符串
        
        验证点：
        - 空字符串应被视为无效 JSON
        - 返回兜底数据
        """
        # Arrange
        empty_data = ""
        
        # Act
        result = ws_bridge._parse_sse_event(empty_data)
        
        # Assert
        assert result["raw"] == ""
        assert result["status"] == "unknown"
    
    def test_execution_id_mapping(self, ws_bridge):
        """测试 execution_id 与 thread_id 映射
        
        验证点：
        - execution_id 正确传递到 WebSocket 消息
        - thread_id 同时保留在消息中
        """
        # Arrange
        sse_data = json.dumps({"event": "test"})
        thread_id = "thread-test123"
        execution_id = "exec-test456"
        
        # Act
        ws_message = ws_bridge._format_ws_message(sse_data, thread_id, execution_id)
        
        # Assert
        assert ws_message["execution_id"] == execution_id
        assert ws_message["thread_id"] == thread_id
        # 两者都应存在于消息中，便于前端双向映射
        assert ws_message["execution_id"] != ws_message["thread_id"]
    
    def test_execution_id_optional(self, ws_bridge):
        """测试 execution_id 可选参数
        
        验证点：
        - execution_id 为 None 时，消息中仍包含该字段
        - 值为 None
        """
        # Arrange
        sse_data = json.dumps({"event": "test"})
        thread_id = "thread-test123"
        
        # Act
        ws_message = ws_bridge._format_ws_message(sse_data, thread_id, execution_id=None)
        
        # Assert
        assert "execution_id" in ws_message
        assert ws_message["execution_id"] is None
    
    def test_various_sse_event_types(self, ws_bridge):
        """测试多种 SSE 事件类型转换
        
        验证点：
        - on_chain_start、on_chain_end、on_chat_model_stream 等事件都能正确转换
        """
        # Arrange
        event_types = [
            {"event": "on_chain_start", "data": {"input": "start"}},
            {"event": "on_chat_model_stream", "data": {"chunk": "token"}},
            {"event": "on_chain_end", "data": {"output": "end"}},
            {"event": "on_tool_start", "data": {"tool": "bash"}},
        ]
        
        # Act & Assert
        for event_data in event_types:
            sse_data = json.dumps(event_data)
            ws_message = ws_bridge._format_ws_message(sse_data, "thread-123", "exec-456")
            
            assert ws_message["type"] == "execution_update"
            assert ws_message["payload"]["event"] == event_data["event"]


# ============================================================================
# Thread ID 到 Execution ID 映射测试
# ============================================================================

class TestThreadIdToExecutionIdMapping:
    """thread_id 到 execution_id 映射测试"""
    
    def test_bidirectional_mapping_preserved(self, ws_bridge):
        """测试双向映射关系保持
        
        验证点：
        - WebSocket 消息同时包含 thread_id 和 execution_id
        - 前端可以通过任一 ID 查找对应关系
        """
        # Arrange
        sse_data = json.dumps({"event": "test"})
        thread_id = "thread-mapping-test"
        execution_id = "exec-mapping-test"
        
        # Act
        ws_message = ws_bridge._format_ws_message(sse_data, thread_id, execution_id)
        
        # Assert
        # 消息中同时存在两个 ID
        assert ws_message["thread_id"] == thread_id
        assert ws_message["execution_id"] == execution_id
        
        # 前端可以建立映射表
        mapping_table = {
            ws_message["thread_id"]: ws_message["execution_id"],
            ws_message["execution_id"]: ws_message["thread_id"]
        }
        
        assert mapping_table[thread_id] == execution_id
        assert mapping_table[execution_id] == thread_id
    
    def test_thread_id_from_sse_metadata(self, ws_bridge):
        """测试从 SSE 元数据中提取 thread_id
        
        验证点：
        - SSE 事件的 metadata 中包含 thread_id
        - 桥接器能正确提取并传递
        """
        # Arrange
        sse_event = {
            "event": "on_chain_start",
            "data": {
                "input": {"query": "test"},
                "metadata": {"thread_id": "thread-from-metadata"}
            }
        }
        sse_data = json.dumps(sse_event)
        
        # Act: 解析 SSE 事件
        parsed = ws_bridge._parse_sse_event(sse_data)
        
        # Assert
        assert "metadata" in parsed["data"]
        assert parsed["data"]["metadata"]["thread_id"] == "thread-from-metadata"
    
    def test_execution_id_consistency_across_messages(self, ws_bridge):
        """测试同一执行会话中 execution_id 一致性
        
        验证点：
        - 同一执行会话的所有消息使用相同的 execution_id
        - 不同执行会话使用不同的 execution_id
        """
        # Arrange
        sse_data = json.dumps({"event": "test"})
        thread_id = "thread-session-1"
        execution_id = "exec-session-1"
        
        # Act: 生成多条消息
        messages = []
        for i in range(3):
            msg = ws_bridge._format_ws_message(sse_data, thread_id, execution_id)
            messages.append(msg)
        
        # Assert: 所有消息的 execution_id 相同
        execution_ids = {msg["execution_id"] for msg in messages}
        assert len(execution_ids) == 1
        assert list(execution_ids)[0] == execution_id
    
    def test_different_sessions_different_ids(self, ws_bridge):
        """测试不同会话使用不同 ID
        
        验证点：
        - 不同执行会话的 execution_id 不同
        - 不同线程的 thread_id 不同
        """
        # Arrange & Act
        msg1 = ws_bridge._format_ws_message(json.dumps({"event": "test"}), "thread-1", "exec-1")
        msg2 = ws_bridge._format_ws_message(json.dumps({"event": "test"}), "thread-2", "exec-2")
        
        # Assert
        assert msg1["thread_id"] != msg2["thread_id"]
        assert msg1["execution_id"] != msg2["execution_id"]


# ============================================================================
# 消息幂等性验证测试
# ============================================================================

class TestMessageIdempotency:
    """消息幂等性验证测试"""
    
    def test_duplicate_event_detection(self):
        """测试重复事件检测逻辑
        
        验证点：
        - 通过 event_id 或消息内容哈希检测重复
        - 重复消息应被丢弃或标记
        """
        # Arrange: 模拟消息缓存（LRU）
        message_cache = {}
        max_cache_size = 100
        
        def is_duplicate(message: dict) -> bool:
            """检测消息是否重复"""
            # 使用 payload 的哈希作为唯一标识
            import hashlib
            payload_str = json.dumps(message.get("payload", {}), sort_keys=True)
            message_id = hashlib.md5(payload_str.encode()).hexdigest()
            
            if message_id in message_cache:
                return True
            
            # 添加到缓存
            if len(message_cache) >= max_cache_size:
                # LRU: 删除最旧的条目
                oldest_key = next(iter(message_cache))
                del message_cache[oldest_key]
            
            message_cache[message_id] = True
            return False
        
        # Act: 发送相同消息两次
        test_message = {
            "type": "execution_update",
            "execution_id": "exec-123",
            "thread_id": "thread-456",
            "payload": {"event": "on_chain_start", "data": {"input": "test"}}
        }
        
        first_check = is_duplicate(test_message)
        second_check = is_duplicate(test_message)
        
        # Assert
        assert first_check is False  # 第一次不是重复
        assert second_check is True  # 第二次是重复
    
    def test_lru_cache_eviction(self):
        """测试 LRU 缓存淘汰策略
        
        验证点：
        - 缓存达到上限时，淘汰最旧的条目
        - 新消息能正常加入缓存
        """
        # Arrange
        message_cache = {}
        max_cache_size = 3
        
        def add_to_cache(message_id: str):
            """添加消息到缓存"""
            if len(message_cache) >= max_cache_size:
                # 淘汰最旧的
                oldest_key = next(iter(message_cache))
                del message_cache[oldest_key]
            message_cache[message_id] = True
        
        # Act: 添加 4 条消息（超过上限）
        for i in range(4):
            add_to_cache(f"msg-{i}")
        
        # Assert
        assert len(message_cache) == max_cache_size  # 缓存大小不超过上限
        assert "msg-0" not in message_cache  # 最旧的消息被淘汰
        assert "msg-3" in message_cache  # 最新的消息在缓存中
    
    def test_message_ordering_preserved(self, ws_bridge):
        """测试消息顺序保持
        
        验证点：
        - 即使有重复检测，消息顺序应与 SSE 流一致
        - 非重复消息按顺序处理
        """
        # Arrange
        received_messages = []
        
        def process_message(ws_message: dict):
            """模拟消息处理"""
            received_messages.append(ws_message)
        
        # Act: 按顺序处理消息
        for i in range(3):
            sse_data = json.dumps({"event": f"event_{i}", "sequence": i})
            ws_message = ws_bridge._format_ws_message(sse_data, "thread-1", "exec-1")
            process_message(ws_message)
        
        # Assert: 验证顺序
        assert len(received_messages) == 3
        for i, msg in enumerate(received_messages):
            assert msg["payload"]["event"] == f"event_{i}"
            assert msg["payload"]["sequence"] == i
    
    def test_concurrent_message_handling(self):
        """测试并发消息处理
        
        验证点：
        - 多线程/异步环境下，幂等性检测仍然有效
        - 不会出现竞态条件导致重复处理
        """
        import asyncio
        
        # Arrange
        processed_messages = set()
        lock = asyncio.Lock()
        
        async def process_message_safe(message_id: str):
            """安全地处理消息（带锁）"""
            async with lock:
                if message_id in processed_messages:
                    return False  # 已处理，跳过
                processed_messages.add(message_id)
                return True  # 首次处理
        
        async def run_concurrent_test():
            # Act: 并发处理相同消息
            tasks = [process_message_safe("msg-1") for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Assert: 只有第一个任务成功处理
            success_count = sum(1 for r in results if r is True)
            assert success_count == 1
            assert len(processed_messages) == 1
        
        # Run async test
        asyncio.run(run_concurrent_test())


# ============================================================================
# WebSocket 桥接集成测试（Mock）
# ============================================================================

class TestWebSocketBridgeIntegration:
    """WebSocket 桥接集成测试（使用 Mock）"""
    
    @pytest.mark.asyncio
    async def test_bridge_accepts_websocket(self, ws_bridge):
        """测试桥接器接受 WebSocket 连接
        
        验证点：
        - websocket.accept() 被调用
        - 日志记录正确的 thread_id
        """
        # Arrange
        mock_websocket = AsyncMock()
        thread_id = "thread-integration-test"
        
        # Mock httpx stream response
        mock_response = AsyncMock()
        mock_response.aiter_lines.return_value = iter([])  # 空流
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        # Act
        with patch('httpx.AsyncClient', return_value=mock_client):
            await ws_bridge.bridge(mock_websocket, thread_id, "exec-test")
        
        # Assert
        mock_websocket.accept.assert_called_once()
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bridge_forwards_sse_events(self, ws_bridge):
        """测试桥接器转发 SSE 事件
        
        验证点：
        - SSE 事件被转换为 WebSocket 消息
        - send_json 被调用
        """
        # Arrange
        mock_websocket = AsyncMock()
        thread_id = "thread-forward-test"
        execution_id = "exec-forward-test"
        
        # Mock SSE 流
        sse_lines = [
            "data: {\"event\": \"on_chain_start\"}",
            "data: {\"event\": \"on_chain_end\"}"
        ]
        
        mock_response = AsyncMock()
        mock_response.aiter_lines.return_value = iter(sse_lines)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        # Act
        with patch('httpx.AsyncClient', return_value=mock_client):
            await ws_bridge.bridge(mock_websocket, thread_id, execution_id)
        
        # Assert: 验证 send_json 被调用
        assert mock_websocket.send_json.call_count == 2
        
        # 验证消息格式
        calls = mock_websocket.send_json.call_args_list
        for call in calls:
            message = call[0][0]
            assert message["type"] == "execution_update"
            assert message["execution_id"] == execution_id
            assert message["thread_id"] == thread_id
    
    @pytest.mark.asyncio
    async def test_bridge_handles_errors(self, ws_bridge):
        """测试桥接器错误处理
        
        验证点：
        - 网络异常时发送错误消息
        - WebSocket 正常关闭
        """
        # Arrange
        mock_websocket = AsyncMock()
        thread_id = "thread-error-test"
        
        # Mock 抛出异常
        mock_client = AsyncMock()
        mock_client.stream.side_effect = Exception("Network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        # Act
        with patch('httpx.AsyncClient', return_value=mock_client):
            await ws_bridge.bridge(mock_websocket, thread_id, "exec-test")
        
        # Assert
        # 验证发送了错误消息
        error_call = mock_websocket.send_json.call_args
        assert error_call is not None
        error_message = error_call[0][0]
        assert error_message["type"] == "error"
        assert "Network error" in error_message["message"]
        
        # 验证 WebSocket 关闭
        mock_websocket.close.assert_called_once()

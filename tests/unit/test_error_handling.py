"""
Unit tests for error handling module.

测试错误处理框架的各个组件。
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.core.error_handling import (
    Result,
    Success,
    Error,
    success,
    error,
    from_exception,
    safe_execute,
    ErrorContext,
    CircuitBreaker,
    retry_on_transient,
)
from src.core.exceptions import (
    CrewException,
    LLMTimeoutError,
    RateLimitError,
    TimeoutError,
    NetworkTimeoutError,
)


# ============================================================================
# Result Type Tests
# ============================================================================


@pytest.mark.unit
def test_success_result():
    """测试成功结果。"""
    result = success({"data": "test"})

    assert isinstance(result, Success)
    assert result.success is True
    assert result.data == {"data": "test"}
    assert result.error is None


@pytest.mark.unit
def test_error_result():
    """测试错误结果。"""
    result = error("Something went wrong", "TEST_ERROR", {"detail": "info"})

    assert isinstance(result, Error)
    assert result.success is False
    assert result.error == "Something went wrong"
    assert result.error_code == "TEST_ERROR"
    assert result.details == {"detail": "info"}


@pytest.mark.unit
def test_from_exception():
    """测试从异常创建错误结果。"""
    exc = LLMTimeoutError("claude", 30)
    result = from_exception(exc)

    assert isinstance(result, Error)
    assert result.success is False
    assert "超时" in result.error
    assert result.error_code == "LLM_TIMEOUT"


# ============================================================================
# Safe Execute Tests
# ============================================================================


@pytest.mark.unit
def test_safe_execute_success():
    """测试安全执行成功。"""
    def test_func(x, y):
        return x + y

    result = safe_execute(test_func, 1, 2)

    assert result.success is True
    assert result.data == 3


@pytest.mark.unit
def test_safe_execute_crew_exception():
    """测试安全执行捕获业务异常。"""
    def test_func():
        raise LLMTimeoutError("claude", 30)

    result = safe_execute(test_func)

    assert result.success is False
    assert "LLM_TIMEOUT" in result.error_code


@pytest.mark.unit
def test_safe_execute_unexpected_exception():
    """测试安全执行捕获未预期异常。"""
    def test_func():
        raise ValueError("Unexpected error")

    result = safe_execute(test_func)

    assert result.success is False
    assert result.error_code == "UNEXPECTED_ERROR"


# ============================================================================
# Error Context Tests
# ============================================================================


@pytest.mark.unit
def test_error_context_success():
    """测试错误上下文成功场景。"""
    with ErrorContext("test_operation", user_id="test-123") as ctx:
        ctx.result = "success"

    assert ctx.success is True
    assert ctx.result == "success"
    assert ctx.error is None


@pytest.mark.unit
def test_error_context_crew_exception():
    """测试错误上下文捕获业务异常。"""
    with ErrorContext("test_operation") as ctx:
        raise LLMTimeoutError("claude", 30)

    assert ctx.success is False
    assert ctx.error is not None
    assert ctx.error_code == "LLM_TIMEOUT"


@pytest.mark.unit
def test_error_context_unexpected_exception():
    """测试错误上下文捕获未预期异常。"""
    with ErrorContext("test_operation") as ctx:
        raise ValueError("Unexpected")

    assert ctx.success is False
    assert ctx.error == "Unexpected"
    assert ctx.error_code == "UNEXPECTED_ERROR"


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


@pytest.mark.unit
def test_circuit_breaker_closed():
    """测试熔断器关闭状态。"""
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

    assert breaker.can_execute() is True
    assert breaker.is_open is False


@pytest.mark.unit
def test_circuit_breaker_opens_after_failures():
    """测试熔断器在连续失败后打开。"""
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

    # 记录 3 次失败
    for _ in range(3):
        breaker.record_failure()

    assert breaker.is_open is True
    assert breaker.can_execute() is False


@pytest.mark.unit
def test_circuit_breaker_half_open_after_timeout():
    """测试熔断器在超时后进入半开状态。"""
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    # 触发熔断
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open is True

    # 等待恢复时间
    time.sleep(0.2)

    # 应该可以执行（半开状态）
    assert breaker.can_execute() is True


@pytest.mark.unit
def test_circuit_breaker_closes_on_success():
    """测试熔断器在成功后关闭。"""
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    # 触发熔断
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open is True

    # 记录成功
    breaker.record_success()

    assert breaker.is_open is False
    assert breaker.failure_count == 0


@pytest.mark.unit
def test_circuit_breaker_decorator():
    """测试熔断器装饰器。"""
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

    @breaker
    def test_func():
        raise ValueError("Test error")

    # 第一次和第二次失败
    with pytest.raises(ValueError):
        test_func()
    with pytest.raises(ValueError):
        test_func()

    # 第三次应该触发熔断
    with pytest.raises(CrewException) as exc_info:
        test_func()

    assert "熔断" in str(exc_info.value)


# ============================================================================
# Retry Decorator Tests
# ============================================================================


@pytest.mark.unit
def test_retry_on_transient_success():
    """测试重试装饰器成功场景。"""
    mock_func = Mock(return_value="success")

    @retry_on_transient(max_attempts=3)
    def test_func():
        return mock_func()

    result = test_func()

    assert result == "success"
    assert mock_func.call_count == 1


@pytest.mark.unit
def test_retry_on_transient_retries():
    """测试重试装饰器重试逻辑。"""
    mock_func = Mock(side_effect=[
        TimeoutError("test", 30),
        TimeoutError("test", 30),
        "success",
    ])

    @retry_on_transient(max_attempts=3, min_wait=0.01, max_wait=0.1)
    def test_func():
        result = mock_func()
        if isinstance(result, Exception):
            raise result
        return result

    result = test_func()

    assert result == "success"
    assert mock_func.call_count == 3


@pytest.mark.unit
def test_retry_on_transient_max_attempts():
    """测试重试装饰器达到最大重试次数。"""
    mock_func = Mock(side_effect=TimeoutError("test", 30))

    @retry_on_transient(max_attempts=3, min_wait=0.01, max_wait=0.1)
    def test_func():
        raise mock_func()

    with pytest.raises(TimeoutError):
        test_func()

    assert mock_func.call_count == 3


@pytest.mark.unit
def test_retry_on_transient_non_retryable():
    """测试重试装饰器不重试非瞬态错误。"""
    mock_func = Mock(side_effect=ValueError("Not retryable"))

    @retry_on_transient(max_attempts=3)
    def test_func():
        raise mock_func()

    with pytest.raises(ValueError):
        test_func()

    # 不应该重试
    assert mock_func.call_count == 1


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_error_handling_integration():
    """测试错误处理集成场景。"""

    @retry_on_transient(max_attempts=3, min_wait=0.01, max_wait=0.1)
    def flaky_operation():
        """模拟不稳定的操作。"""
        import random
        if random.random() < 0.7:  # 70% 失败率
            raise NetworkTimeoutError("https://api.example.com", 30)
        return {"data": "success"}

    # 使用 safe_execute 包装
    result = safe_execute(flaky_operation)

    # 应该最终成功或失败
    assert isinstance(result, (Success, Error))

    if result.success:
        assert result.data == {"data": "success"}
    else:
        assert "NETWORK_TIMEOUT" in result.error_code or "UNEXPECTED_ERROR" in result.error_code

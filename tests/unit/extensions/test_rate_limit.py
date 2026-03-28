"""Tests for converge.extensions.rate_limit."""

from converge.core.message import Message
from converge.core.topic import Topic
from converge.extensions.rate_limit import RateLimiter, RateLimitHook, TokenBucketConfig
from converge.observability.metrics import MetricsCollector


def test_rate_limiter_global_bucket_enforced():
    limiter = RateLimiter(global_config=TokenBucketConfig(capacity=1.0, refill_tokens_per_sec=0.0))
    msg = Message(sender="a1", payload={})
    assert limiter.allow_message(msg, direction="egress") is True
    assert limiter.allow_message(msg, direction="egress") is False


def test_rate_limiter_sender_and_topic_keys():
    limiter = RateLimiter(
        sender_config=TokenBucketConfig(capacity=1.0, refill_tokens_per_sec=0.0),
        topic_config=TokenBucketConfig(capacity=1.0, refill_tokens_per_sec=0.0),
    )
    msg_a = Message(sender="a1", payload={}, topics=[Topic("a.b")])
    msg_b = Message(sender="a2", payload={}, topics=[Topic("a.b")])
    assert limiter.allow_message(msg_a, direction="ingress") is True
    assert limiter.allow_message(msg_a, direction="ingress") is False
    assert limiter.allow_message(msg_b, direction="ingress") is False


def test_rate_limit_hook_metrics_for_ingress_and_egress_drops():
    limiter = RateLimiter(global_config=TokenBucketConfig(capacity=0.0, refill_tokens_per_sec=0.0))
    metrics = MetricsCollector()
    hook = RateLimitHook(limiter, metrics_collector=metrics)
    msg = Message(sender="a1", payload={})
    assert hook.pre_send(msg) is None
    assert hook.post_receive(msg) is None
    snap = metrics.snapshot()
    assert snap["counters"]["rate_limit_egress_dropped_total"] == 1
    assert snap["counters"]["rate_limit_ingress_dropped_total"] == 1

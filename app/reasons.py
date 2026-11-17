REASONS = {
    "BAD_COLUMNS": "字段数量不符", "EMPTY_VALUE": "必要值为空",
    "DUPLICATE_CONFLICT": "同一业务键取值冲突", "TRUNCATED": "尾记录不完整",
    "INVALID_VALUE": "值不符合定义", "STALE_VERSION": "提交版本已过期",
    "NEGATIVE_WEIGHT": "权重为负", "ZERO_WEIGHT_GROUP": "权重合计为零",
    "CAP_LIMIT": "封顶不足，保留未分配款",
    "BATCH_NOT_FOUND": "批次不存在", "BATCH_NOT_SETTLED": "批次未结，不能复算",
}

def reason(code: str) -> str:
    return REASONS.get(code, "未登记原因")

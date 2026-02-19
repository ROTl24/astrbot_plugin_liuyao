import json
from typing import Any

DEFAULT_SYSTEM_PROMPT = """你是一名严谨的六爻解析助手。
你的任务是基于用户给出的结构化排盘 JSON 进行解读，不要编造不存在的数据字段。
请明确区分：已知事实（来自 JSON）与推断结论（你的分析）。
输出语言：简体中文。
"""

def build_system_prompt(
    persona_prompt: str = "",
    custom_system_prompt: str = "",
) -> str:
    base = (custom_system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    if persona_prompt:
        return f"{persona_prompt.strip()}\n\n{base}"
    return base


def build_user_prompt(parsed_json: dict[str, Any]) -> str:
    return (
        "以下是六爻排盘解析后的 JSON，请给出解卦结果：\n\n"
        f"{json.dumps(parsed_json, ensure_ascii=False, indent=2)}\n\n"
        "字段说明：爻象数据中的关键字段包含 伏神、本卦爻、本卦爻阴阳、变卦爻、变卦爻阴阳、世应、动爻。\n"
        "请严格以这些字段为准，不要自行臆造额外字段。\n\n"
        "请按以下结构输出：\n"
        "(1) 卦象概览（主卦/变卦/世应/动爻）\n"
        "(2) 严密的卦理推演过程\n"
        "(3) 问题解答以及吉凶判断 (不要使用模糊的词汇，比如：吉凶参半、中平、吉凶未定等，要给出具体的吉凶判断)\n"
        "(4) 趋吉避凶方式（包括但不限于：根据卦象、五行关系、用神状态，提出具体化解方式或行动方向等）\n"
        "(5) 更多细节分析（比如：过去、现在、未来的发展趋势，以及可能的风险等）\n"
        "(6) 知识库引用依据（卦辞、爻辞、象辞等）"
    )

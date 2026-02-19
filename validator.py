from typing import Any


def validate(parsed_json: dict[str, Any]) -> tuple[bool, list[dict[str, str]]]:
    errors: list[dict[str, str]] = list(parsed_json.get("errors", []))
    yao_list = parsed_json.get("爻象数据", [])

    if len(yao_list) != 6:
        errors.append(
            {
                "code": "E101",
                "message": f"必须识别到 6 行爻象，当前识别到 {len(yao_list)} 行。",
            },
        )

    indexes = [item.get("index") for item in yao_list if isinstance(item, dict)]
    if sorted(indexes) != [1, 2, 3, 4, 5, 6]:
        errors.append(
            {
                "code": "E102",
                "message": f"index 必须完整为 6..1 且不重复，当前为 {indexes}。",
            },
        )

    for item in yao_list:
        if not isinstance(item, dict):
            continue
        is_moving = bool(item.get("动爻"))
        if is_moving and (not item.get("变卦爻") or not item.get("变卦爻阴阳")):
            errors.append(
                {
                    "code": "E201",
                    "message": f"第 {item.get('index')} 爻为动爻，但缺少变卦爻/变卦爻阴阳。",
                },
            )

    parsed_json["errors"] = errors
    return len(errors) == 0, errors


def format_errors(errors: list[dict[str, str]]) -> str:
    if not errors:
        return "未知错误。"
    lines = ["解析失败："]
    for err in errors:
        lines.append(f"- {err.get('code', 'E000')}: {err.get('message', '')}")
    lines.append("请补充缺失字段后重新发送 /liuyao。")
    return "\n".join(lines)


if __name__ == "__main__":
    broken = {
        "基础信息": {},
        "爻象数据": [{"index": 6, "动爻": True, "变卦爻": None, "变卦爻阴阳": None}],
        "errors": [],
    }
    ok, errs = validate(broken)
    print("ok =", ok)
    print(format_errors(errs))

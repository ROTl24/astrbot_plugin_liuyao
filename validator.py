from typing import Any

from .keys import (
    BASE_INFO_KEY,
    ERRORS_KEY,
    FIELD_BIAN_YAO,
    FIELD_BIAN_YINYANG,
    FIELD_INDEX,
    FIELD_MOVING,
    YAO_DATA_KEY,
)


def validate(parsed_json: dict[str, Any]) -> tuple[bool, list[dict[str, str]]]:
    errors: list[dict[str, str]] = list(parsed_json.get(ERRORS_KEY, []))
    yao_list = parsed_json.get(YAO_DATA_KEY, [])

    if len(yao_list) != 6:
        errors.append(
            {
                "code": "E101",
                "message": f"必须识别到 6 行爻象，当前识别到 {len(yao_list)} 行。",
            },
        )

    indexes = [item.get(FIELD_INDEX) for item in yao_list if isinstance(item, dict)]
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
        is_moving = bool(item.get(FIELD_MOVING))
        if is_moving and (
            not item.get(FIELD_BIAN_YAO) or not item.get(FIELD_BIAN_YINYANG)
        ):
            errors.append(
                {
                    "code": "E201",
                    "message": (
                        f"第 {item.get(FIELD_INDEX)} 爻为动爻，"
                        "但缺少变卦爻/变卦爻阴阳。"
                    ),
                },
            )

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
        BASE_INFO_KEY: {},
        YAO_DATA_KEY: [
            {
                FIELD_INDEX: 6,
                FIELD_MOVING: True,
                FIELD_BIAN_YAO: None,
                FIELD_BIAN_YINYANG: None,
            },
        ],
        ERRORS_KEY: [],
    }
    ok, errs = validate(broken)
    print("ok =", ok)
    print(format_errors(errs))

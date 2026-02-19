import json
import re
from dataclasses import dataclass
from typing import Any

from .keys import BASE_INFO_KEY, ERRORS_KEY, YAO_DATA_KEY

SIX_GOD_MAP = {
    "虎": "白虎",
    "白虎": "白虎",
    "蛇": "螣蛇",
    "螣蛇": "螣蛇",
    "勾": "勾陈",
    "勾陈": "勾陈",
    "雀": "朱雀",
    "朱雀": "朱雀",
    "龙": "青龙",
    "青龙": "青龙",
    "玄": "玄武",
    "玄武": "玄武",
}

KIN_MAP = {
    "财": "妻财",
    "官": "官鬼",
    "孙": "子孙",
    "兄": "兄弟",
    "父": "父母",
}

BRANCH_WUXING = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}

MOVING_MARKERS = {"X", "Χ", "×", "O", "○"}


@dataclass
class ParsedYaoLine:
    index: int
    pos: str
    yin_yang: str
    six_god: str | None
    fu_shen: str | None
    ben_yao: str | None
    ben_hua: str | None
    moving: bool
    shi_ying: str | None
    bian_yao: str | None
    bian_hua: str | None
    raw: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "pos": self.pos,
            "阴阳": self.yin_yang,
            "六神": self.six_god,
            "伏神": self.fu_shen,
            "本卦爻": self.ben_yao,
            "本卦爻阴阳": self.ben_hua,
            "世应": self.shi_ying,
            "动爻": self.moving,
            "变卦爻": self.bian_yao,
            "变卦爻阴阳": self.bian_hua,
            "raw": self.raw,
        }


class LiuYaoParser:
    @staticmethod
    def parse(raw_text: str) -> dict[str, Any]:
        # Guard against oversized payloads to avoid blocking the event loop too long.
        if len(raw_text or "") > 12000:
            return {
                BASE_INFO_KEY: {},
                YAO_DATA_KEY: [],
                ERRORS_KEY: [
                    {
                        "code": "E001",
                        "message": "输入文本过长，请控制在 12000 字以内。",
                    },
                ],
            }
        lines = [
            line.rstrip() for line in (raw_text or "").splitlines() if line.strip()
        ]
        base_info = LiuYaoParser._parse_base_info(lines)
        yao_lines = LiuYaoParser._parse_yao_lines(lines)

        return {
            BASE_INFO_KEY: base_info,
            YAO_DATA_KEY: [item.to_dict() for item in yao_lines],
            ERRORS_KEY: [],
        }

    @staticmethod
    def _parse_base_info(lines: list[str]) -> dict[str, Any]:
        text = "\n".join(lines)
        time_str = LiuYaoParser._extract_first(text, r"时间[:：]\s*(.+)")
        question = LiuYaoParser._extract_first(text, r"占问[:：]\s*(.+)")
        four_pillars = LiuYaoParser._extract_pillars(lines)
        kong_wang = LiuYaoParser._extract_kong_wang(lines)

        ben_full = LiuYaoParser._extract_first(text, r"本卦[:：]\s*([^\n]+)")
        bian_full = LiuYaoParser._extract_first(text, r"变卦[:：]\s*([^\n]+)")

        ben_name, ben_gong = LiuYaoParser._parse_gua_meta(ben_full)
        bian_name, bian_gong = LiuYaoParser._parse_gua_meta(bian_full)

        return {
            "占问事由": question,
            "起卦时间": time_str,
            "四柱": four_pillars,
            "空亡_raw": kong_wang,
            "主卦": ben_name,
            "变卦": bian_name,
            "所属宫位": ben_gong or bian_gong,
        }

    @staticmethod
    def _parse_yao_lines(lines: list[str]) -> list[ParsedYaoLine]:
        yao_candidates = []
        for line in lines:
            normalized = LiuYaoParser._normalize_space(line)
            if not normalized:
                continue
            first = normalized.split(" ", 1)[0]
            if first in SIX_GOD_MAP:
                yao_candidates.append(line)

        parsed: list[ParsedYaoLine] = []
        index = 6
        for line in yao_candidates[:6]:
            parsed.append(LiuYaoParser._parse_single_yao(index, line))
            index -= 1
        return parsed

    @staticmethod
    def _parse_single_yao(index: int, line: str) -> ParsedYaoLine:
        raw = line.strip()
        normalized = LiuYaoParser._normalize_space(raw)
        moving = any(marker in raw for marker in MOVING_MARKERS)

        parts = normalized.split(" ")
        if len(parts) < 4:
            return ParsedYaoLine(
                index=index,
                pos=LiuYaoParser._pos_of(index),
                yin_yang="未知",
                six_god=None,
                fu_shen=None,
                ben_yao=None,
                ben_hua=None,
                moving=moving,
                shi_ying=None,
                bian_yao=None,
                bian_hua=None,
                raw=raw,
            )

        god_raw, left_token, ben_token = parts[0], parts[1], parts[2]
        tail = " ".join(parts[3:])
        draw_pattern = re.compile(r"(?:-\s*-|—)\s*[XΧ×O○]?")
        first_draw = draw_pattern.search(tail)
        if not first_draw:
            return ParsedYaoLine(
                index=index,
                pos=LiuYaoParser._pos_of(index),
                yin_yang="未知",
                six_god=SIX_GOD_MAP.get(god_raw, god_raw),
                fu_shen=LiuYaoParser._expand_rel_token(left_token),
                ben_yao=LiuYaoParser._expand_rel_token(ben_token),
                ben_hua=None,
                moving=moving,
                shi_ying=None,
                bian_yao=None,
                bian_hua=None,
                raw=raw,
            )

        ben_hua = LiuYaoParser._detect_draw(first_draw.group(0))
        rest = tail[first_draw.end() :].strip()
        right_clean, shi_ying = LiuYaoParser._extract_shi_ying(rest)

        second_draw = draw_pattern.search(right_clean)
        if second_draw:
            right_token_segment = right_clean[: second_draw.start()].strip()
            bian_hua = LiuYaoParser._detect_draw(second_draw.group(0))
        else:
            right_token_segment = right_clean
            bian_hua = None

        bian_token = LiuYaoParser._extract_yao_token(right_token_segment)

        yin_yang = "阳爻" if ben_hua == "阳" else "阴爻" if ben_hua == "阴" else "未知"
        return ParsedYaoLine(
            index=index,
            pos=LiuYaoParser._pos_of(index),
            yin_yang=yin_yang,
            six_god=SIX_GOD_MAP.get(god_raw, god_raw),
            fu_shen=LiuYaoParser._expand_rel_token(left_token),
            ben_yao=LiuYaoParser._expand_rel_token(ben_token),
            ben_hua=ben_hua,
            moving=moving,
            shi_ying=shi_ying,
            bian_yao=LiuYaoParser._expand_rel_token(bian_token) if bian_token else None,
            bian_hua=bian_hua,
            raw=raw,
        )

    @staticmethod
    def _normalize_space(text: str) -> str:
        text = text.replace("\u3000", " ")
        text = text.replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _detect_draw(text: str) -> str | None:
        t = LiuYaoParser._normalize_space(text)
        if "—" in t:
            return "阳"
        if re.search(r"-\s*-|--", t):
            return "阴"
        return None

    @staticmethod
    def _extract_shi_ying(text: str) -> tuple[str, str | None]:
        t = LiuYaoParser._normalize_space(text)
        shi_ying: str | None = None
        if t.startswith("世 "):
            shi_ying = "世"
            t = t[2:]
        elif t == "世":
            shi_ying = "世"
            t = ""
        elif t.startswith("应 "):
            shi_ying = "应"
            t = t[2:]
        elif t == "应":
            shi_ying = "应"
            t = ""
        return LiuYaoParser._normalize_space(t), shi_ying

    @staticmethod
    def _extract_yao_token(text: str) -> str | None:
        t = LiuYaoParser._normalize_space(text)
        if not t:
            return None
        first = t.split(" ", 1)[0]
        if first in {"—", "-", "--"}:
            return None
        return first

    @staticmethod
    def _expand_rel_token(token: str | None) -> str | None:
        if not token:
            return None
        token = token.strip()
        if len(token) < 2:
            return token

        kin = token[0]
        branch = token[1]
        kin_full = KIN_MAP.get(kin)
        wx = BRANCH_WUXING.get(branch)
        if kin_full and wx:
            return f"{kin_full}{branch}{wx}"
        return token

    @staticmethod
    def _extract_first(text: str, pattern: str) -> str | None:
        m = re.search(pattern, text)
        return m.group(1).strip() if m else None

    @staticmethod
    def _extract_pillars(lines: list[str]) -> str | None:
        for line in lines:
            normalized = LiuYaoParser._normalize_space(line)
            if all(word in normalized for word in ("年", "月", "日", "时")):
                if not any(
                    prefix in normalized for prefix in ("时间", "本卦", "变卦", "占问")
                ):
                    return normalized
        return None

    @staticmethod
    def _extract_kong_wang(lines: list[str]) -> str | None:
        for line in lines:
            normalized = LiuYaoParser._normalize_space(line)
            if (
                "空" in normalized
                and "年" not in normalized
                and "时间" not in normalized
            ):
                if normalized.count("空") >= 1 and "卦" not in normalized:
                    return normalized
        return None

    @staticmethod
    def _parse_gua_meta(text: str | None) -> tuple[str | None, str | None]:
        if not text:
            return None, None
        t = LiuYaoParser._normalize_space(text)
        m = re.match(r"([^/]+)(?:/([^·]+))?(?:·\d+)?", t)
        if not m:
            return t, None
        gua_name = (m.group(1) or "").strip() or None
        gong = (m.group(2) or "").strip() or None
        return gua_name, gong

    @staticmethod
    def _pos_of(index: int) -> str:
        mapping = {6: "上六", 5: "五爻", 4: "四爻", 3: "三爻", 2: "二爻", 1: "初爻"}
        return mapping.get(index, str(index))


if __name__ == "__main__":
    SAMPLE = """灵光象吉·六爻排盘
时间：2026年02月17日 18:11:37
占问：猫猫在哪
丙午年 庚寅月 壬戌日 己酉时
寅卯空 午未空 子丑空 寅卯空
本卦：地风升/震宫·5
变卦：水风井/震宫·6
虎 财戌 官酉 - -     　 父子 - -
蛇 官申 父亥 - -Χ 　 财戌 —
勾 孙午 财丑 - -     世 官申 - -
雀 财辰 官酉 —     　 官酉 —
龙 兄寅 父亥 —     　 父亥 —
玄 父子 财丑 - -     应 财丑 - -
"""
    print(json.dumps(LiuYaoParser.parse(SAMPLE), ensure_ascii=False, indent=2))

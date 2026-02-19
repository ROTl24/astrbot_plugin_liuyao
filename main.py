import json
import re
from typing import Any

from astrbot.api import logger, sp
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.astr_main_agent_resources import retrieve_knowledge_base

from .parser import LiuYaoParser
from .prompt import build_system_prompt, build_user_prompt
from .validator import format_errors, validate


@register("astrbot_plugin_liuyao", "Xiaolu", "六爻占卜解析助手", "0.1.0")
class LiuYaoPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context, config)
        self.config = config or {}

    async def initialize(self) -> None:
        logger.info("astrbot_plugin_liuyao loaded")

    @filter.command("liuyao")
    async def liuyao(self, event: AstrMessageEvent):
        """解析灵光象吉六爻排盘并调用 AI 生成解卦文本"""
        raw_text = self._extract_raw_text(event.message_str)
        if not raw_text:
            yield event.plain_result(
                "插件已加载。请在同一条消息中发送 `/liuyao` + 六爻排盘纯文本。",
            )
            return

        parsed = LiuYaoParser.parse(raw_text)
        ok, errors = validate(parsed)
        if not ok:
            yield event.plain_result(format_errors(errors))
            if self._cfg_bool("debug", False):
                yield event.plain_result(
                    "解析 JSON（debug）:\n"
                    + json.dumps(parsed, ensure_ascii=False, indent=2),
                )
            return

        result_text = await self._ask_ai_for_interpretation(event, parsed)
        if not result_text:
            yield event.plain_result(
                "排盘解析成功，但 AI 解卦失败。请检查模型配置后重试。",
            )
            return

        yield event.plain_result(result_text)
        if self._cfg_bool("debug", False):
            yield event.plain_result(
                "解析 JSON（debug）:\n"
                + json.dumps(parsed, ensure_ascii=False, indent=2),
            )

    async def terminate(self) -> None:
        logger.info("astrbot_plugin_liuyao terminated")

    async def _ask_ai_for_interpretation(
        self,
        event: AstrMessageEvent,
        parsed_json: dict[str, Any],
    ) -> str | None:
        provider = self.context.get_using_provider(event.unified_msg_origin)
        if not provider:
            logger.error("No provider configured for current session.")
            return None

        user_prompt = build_user_prompt(parsed_json)
        persona_prompt = await self._resolve_persona_prompt(event)
        system_prompt = build_system_prompt(
            persona_prompt=persona_prompt,
            custom_system_prompt=self._cfg_str("custom_system_prompt", ""),
        )
        kb_context = await self._resolve_kb_context(event, user_prompt)
        if kb_context:
            system_prompt += f"\n\n[Related Knowledge Base Results]\n{kb_context}"

        try:
            if self._cfg_bool("stream", False):
                final_text = ""
                async for chunk in provider.text_chat_stream(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                ):
                    text = (chunk.completion_text or "").strip()
                    if text:
                        final_text = self._merge_stream_text(final_text, text)
                return final_text or None

            resp = await provider.text_chat(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )
            return (resp.completion_text or "").strip() or None
        except Exception as exc:
            logger.error(f"Liuyao AI request failed: {exc!s}")
            return None

    async def _resolve_kb_context(
        self, event: AstrMessageEvent, query: str
    ) -> str | None:
        kb_collection = (self.config.get("kb_collection") or "").strip()
        if kb_collection:
            try:
                cfg = self.context.get_config(umo=event.unified_msg_origin)
                kb_result = await self.context.kb_manager.retrieve(
                    query=query,
                    kb_names=[kb_collection],
                    top_k_fusion=cfg.get("kb_fusion_top_k", 20),
                    top_m_final=cfg.get("kb_final_top_k", 5),
                )
                if kb_result:
                    return kb_result.get("context_text", "")
            except Exception as exc:
                logger.error(f"Custom kb_collection retrieve failed: {exc!s}")
            return None

        try:
            return await retrieve_knowledge_base(
                query=query,
                umo=event.unified_msg_origin,
                context=self.context,
            )
        except Exception as exc:
            logger.error(f"Default KB retrieve failed: {exc!s}")
            return None

    async def _resolve_persona_prompt(self, event: AstrMessageEvent) -> str:
        persona_id = (self.config.get("persona_id") or "").strip()

        if not persona_id:
            session_cfg = await sp.get_async(
                scope="umo",
                scope_id=event.unified_msg_origin,
                key="session_service_config",
                default={},
            )
            persona_id = (session_cfg.get("persona_id") or "").strip()

        if not persona_id:
            cfg = self.context.get_config(umo=event.unified_msg_origin)
            persona_id = (
                cfg.get("provider_settings", {})
                .get("default_personality", "default")
                .strip()
            )

        if not persona_id or persona_id == "default":
            return ""

        try:
            persona = await self.context.persona_manager.get_persona(persona_id)
            return (persona.system_prompt or "").strip()
        except Exception as exc:
            logger.error(f"Resolve persona failed({persona_id}): {exc!s}")
            return ""

    @staticmethod
    def _extract_raw_text(message_str: str) -> str:
        text = (message_str or "").strip()
        text = re.sub(r"^/liuyao(?:\s+|$)", "", text, count=1, flags=re.IGNORECASE)
        return text.strip()

    def _cfg_bool(self, key: str, default: bool) -> bool:
        value = self.config.get(key, default)
        return bool(value)

    def _cfg_str(self, key: str, default: str) -> str:
        value = self.config.get(key, default)
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _merge_stream_text(current: str, new_chunk: str) -> str:
        if not current:
            return new_chunk
        if new_chunk.startswith(current):
            return new_chunk
        return current + new_chunk

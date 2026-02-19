# astrbot_plugin_liuyao

六爻占卜解析助手（AstrBot 插件）。

插件接收“灵光象吉·六爻排盘”的纯文本，先做结构化解析与校验，校验通过后再调用 AstrBot 的 AI 进行解卦输出。  
支持结合 AstrBot 已配置的知识库进行增强解析；未配置知识库时也可正常使用。

## 功能特性

- 指令触发：`/liuyao`
- 解析灵光象吉排盘文本为结构化 JSON
- 内置校验器，失败时返回明确错误码，不调用 AI
- 支持自定义系统提示词（留空回退默认提示词）
- 支持调试模式回显解析 JSON（便于对盘）
- 支持流式模型调用（插件内部整合为最终文本返回）

## 工作流

1. 用户发送 `/liuyao` + 排盘原文（同一条消息）
2. 插件执行 `LiuYaoParser.parse(raw_text)`
3. 插件执行 `validate(parsed_json)`
4. 校验通过后，组装 `System Prompt + JSON` 调用 AstrBot LLM
5. 返回解卦结果；若 `debug=true` 额外回显 JSON

## 安装方式

将插件目录放入：

`AstrBot/data/plugins/astrbot_plugin_liuyao`

然后在 AstrBot WebUI 中重载/启用该插件。

## 使用示例

```text
/liuyao
灵光象吉·六爻排盘
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
```

## 配置说明（_conf_schema）

- `custom_system_prompt`：自定义系统提示词（留空走默认）
- `stream`：是否使用流式模型调用
- `debug`：是否额外回显解析 JSON

## 校验错误码

- `E101`：必须识别到 6 行爻象
- `E102`：`index` 必须完整为 `6..1` 且不重复
- `E201`：`动爻=true` 但缺少 `变卦爻/变卦爻阴阳`

## 依赖与参考

- [AstrBot](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发文档（中文）](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot Plugin Docs (English)](https://docs.astrbot.app/en/dev/star/plugin-new.html)

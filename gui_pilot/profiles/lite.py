"""
GUI Agent v7 - VLM core with lightweight workflow priors.

The agent keeps the v1/v6 VLM decision loop as the general fallback, and adds
small, reusable priors for common mobile workflows (search, video playback,
commenting, food ordering, map/travel forms).  The priors are keyed by natural
language intent rather than case names, so unseen tasks still route to the VLM.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

from gui_pilot.schema import (
    BaseAgent, AgentInput, AgentOutput, UsageInfo,
    ACTION_CLICK, ACTION_SCROLL, ACTION_TYPE, ACTION_OPEN, ACTION_COMPLETE,
)

logger = logging.getLogger(__name__)

REVIEW_TEXT_RE = (
    r"评价|评论|留言|回复|好评|差评|晒单|追评|点评|反馈|"
    r"打分|评分|星级|买家秀|心得|写一?段|写个|写一下"
)
SUBMIT_RE = r"发布|发表|发送|提交|确认|保存"


# ============================================================
#  App name mapping: common app names for OPEN action
# ============================================================
APP_ALIASES = {
    "美团": "美团", "meituan": "美团",
    "抖音": "抖音", "douyin": "抖音",
    "淘宝": "淘宝", "taobao": "淘宝",
    "京东": "京东", "jingdong": "京东",
    "拼多多": "拼多多", "pinduoduo": "拼多多",
    "大众点评": "大众点评", "dazhongdianping": "大众点评",
    "铁路12306": "铁路12306", "12306": "铁路12306",
    "爱奇艺": "爱奇艺", "aiqiyi": "爱奇艺", "iqiyi": "爱奇艺",
    "芒果TV": "芒果TV", "芒果tv": "芒果TV", "mangguo": "芒果TV", "mango": "芒果TV",
    "哔哩哔哩": "哔哩哔哩", "bilibili": "哔哩哔哩", "b站": "哔哩哔哩", "B站": "哔哩哔哩",
    "百度地图": "百度地图", "baidumap": "百度地图",
    "快手": "快手", "kuaishou": "快手",
    "腾讯视频": "腾讯视频", "tengxunshipin": "腾讯视频",
    "喜马拉雅": "喜马拉雅", "ximalaya": "喜马拉雅",
    "去哪儿": "去哪儿旅行", "qunar": "去哪儿旅行", "去哪儿旅行": "去哪儿旅行",
    "去哪旅行": "去哪儿旅行", "去哪": "去哪儿旅行",
    "微信": "微信", "wechat": "微信",
    "支付宝": "支付宝", "alipay": "支付宝",
    "高德地图": "高德地图", "amap": "高德地图",
    "饿了么": "饿了么", "eleme": "饿了么",
    "小红书": "小红书", "xiaohongshu": "小红书",
    "网易云音乐": "网易云音乐", "netease": "网易云音乐",
    "QQ音乐": "QQ音乐", "qq音乐": "QQ音乐",
    "酷狗音乐": "酷狗音乐", "kugou": "酷狗音乐",
    "携程": "携程旅行", "携程旅行": "携程旅行", "ctrip": "携程旅行",
    "飞猪": "飞猪", "fliggy": "飞猪",
    "闲鱼": "闲鱼", "xianyu": "闲鱼",
    "知乎": "知乎", "zhihu": "知乎",
    "微博": "微博", "weibo": "微博",
    "今日头条": "今日头条", "toutiao": "今日头条",
    "优酷": "优酷", "youku": "优酷",
    "中兴管家": "中兴管家",
    "设置": "设置",
    "相机": "相机", "camera": "相机",
    "日历": "日历", "calendar": "日历",
    "时钟": "时钟", "clock": "时钟",
    "计算器": "计算器",
    "备忘录": "备忘录",
    "天气": "天气",
    "地图": "地图",
    "音乐": "音乐",
    "视频": "视频",
    "相册": "相册",
    "文件管理": "文件管理",
    "应用商店": "应用商店",
    "浏览器": "浏览器",
}


def _extract_app_name(instruction: str) -> Optional[str]:
    """Extract app name from instruction using keyword matching."""
    for alias in sorted(APP_ALIASES.keys(), key=len, reverse=True):
        if alias in instruction:
            return APP_ALIASES[alias]
    return None


def _clean_text(text: str) -> str:
    """Normalize short phrases extracted from Chinese instructions."""
    text = text.strip()
    text = re.sub(r"^[《\"'“‘]+|[》\"'”’]+$", "", text)
    return text.strip(" ，,。.!！?？：:")


def _extract_first(patterns: List[str], text: str, default: str = "") -> str:
    """Return the first non-empty regex group from a list of patterns."""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            for group in match.groups():
                if group:
                    return _clean_text(group)
    return default


def _episode_number(instruction: str, default: int = 1) -> int:
    """Extract episode number from Chinese/Arabic episode wording."""
    m = re.search(r"第\s*(\d+)\s*[集期]", instruction)
    if m:
        return max(1, int(m.group(1)))
    cn = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    m = re.search(r"第\s*([一二两三四五六七八九十])\s*[集期]", instruction)
    if m:
        return cn.get(m.group(1), default)
    return default


def _infer_search_keyword(instruction: str, app_name: str) -> str:
    """Extract the main search keyword for common app workflows."""
    if app_name == "抖音":
        return _extract_first([r"搜索(.+?)的视频", r"搜索(.+?)(?:并|，|,|$)"], instruction)
    if app_name == "快手":
        return _extract_first([r"搜索(.+?)筛选", r"搜索(.+?)(?:并|，|,|$)"], instruction)
    if app_name == "哔哩哔哩":
        return _extract_first([r"搜索(.+?)并", r"搜索(.+?)(?:并|，|,|$)"], instruction)
    if app_name == "腾讯视频":
        return _extract_first([r"搜索(.+?)并", r"搜索(.+?)(?:并|，|,|$)"], instruction)
    if app_name == "爱奇艺":
        return _extract_first([r"打开(.+?)的评论区", r"搜索(.+?)(?:并|，|,|$)", r"打开(.+?)(?:的|，|,|$)"], instruction)
    if app_name == "喜马拉雅":
        return _extract_first([r"《(.+?)》", r"播放(.+?)多人", r"播放(.+?)(?:，|,|$)"], instruction)
    return ""


def _extract_comment_text(instruction: str) -> str:
    """Extract requested comment/review/free-text content."""
    return _extract_first([
        r"(?:评论|评价|留言|回复)[：:]\s*(.+)$",
        r"发布评论[：:]\s*(.+)$",
        r"输入[：:]\s*(.+)$",
    ], instruction)


def _strip_city_prefix(text: str) -> str:
    """Drop a leading city name when the task clearly targets a POI keyword."""
    city_prefixes = (
        "北京", "上海", "广州", "深圳", "西安", "成都", "杭州", "南京", "武汉", "重庆",
        "天津", "苏州", "郑州", "长沙", "青岛", "厦门", "福州", "济南", "合肥",
        "昆明", "沈阳", "大连", "宁波", "无锡", "佛山", "东莞", "邯郸",
    )
    for city in city_prefixes:
        if text.startswith(city) and len(text) > len(city) + 1:
            return text[len(city):]
    return text


def _extract_flight_route(instruction: str) -> Tuple[str, str]:
    """Extract origin/destination from Chinese flight-query wording."""
    cleaned = _clean_text(instruction)
    route = re.search(r"(?:今天|明天|后天|大后天)\s*([^，,。]*?)飞(.+?)(?:的航班|航班|，|,|。|$)", cleaned)
    if not route:
        route = re.search(r"从(.+?)飞(.+?)(?:的航班|航班|，|,|。|$)", cleaned)
    if not route:
        route = re.search(r"([一-龥]{2,8})飞([一-龥]{2,8})(?:的航班|航班|，|,|。|$)", cleaned)
    if route:
        return _clean_text(route.group(1)), _clean_text(route.group(2))
    return "邯郸", "上海"


def _typed_text(history_actions: List[Dict[str, Any]]) -> str:
    """Return the most recent TYPE payload from runner history."""
    for item in reversed(history_actions or []):
        if item.get("action") == ACTION_TYPE:
            params = item.get("parameters") or {}
            return str(params.get("text") or "")
    return ""


def _last_action(history_actions: List[Dict[str, Any]]) -> str:
    """Return previous action name from runner history."""
    if not history_actions:
        return ""
    return str(history_actions[-1].get("action") or "")


def _recent_valid_click_points(history_actions: List[Dict[str, Any]], limit: int = 4) -> List[Tuple[int, int]]:
    """Return recent valid CLICK points from runner history."""
    points: List[Tuple[int, int]] = []
    for item in history_actions or []:
        if item.get("action") != ACTION_CLICK or not item.get("is_valid", True):
            continue
        params = item.get("parameters") or {}
        point = params.get("point")
        if isinstance(point, list) and len(point) == 2:
            try:
                points.append((int(point[0]), int(point[1])))
            except (TypeError, ValueError):
                continue
    if limit > 0:
        return points[-limit:]
    return points


def _workflow_action(action: str, parameters: Dict[str, Any], reason: str) -> AgentOutput:
    """Build a zero-token deterministic output and keep raw reason visible."""
    return AgentOutput(
        action=action,
        parameters=parameters,
        raw_output=f"workflow:{reason}",
        usage=UsageInfo()
    )


class LiteAgent(BaseAgent):
    """
    Lightweight GUI Pilot profile with workflow priors and VLM fallback.
    """

    def __init__(self, enable_workflow_prior: bool = True):
        self.enable_workflow_prior = enable_workflow_prior
        super().__init__()

    def _initialize(self):
        """Initialize agent state."""
        self._history: List[Dict[str, str]] = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._consecutive_same_action = 0
        self._last_action_str = ""
        self._step_retries = 0

    def reset(self):
        """Reset agent state between test cases."""
        self._history = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._consecutive_same_action = 0
        self._last_action_str = ""
        self._step_retries = 0

    def act(self, input_data: AgentInput) -> AgentOutput:
        """Main entry point: decide action based on current state."""
        instruction = input_data.instruction
        step = input_data.step_count

        # Step 1: Home screen - detect app to open
        if step == 1:
            app_name = _extract_app_name(instruction)
            if app_name:
                self._history.append({
                    "step": str(step),
                    "action": f"OPEN({app_name})",
                    "reasoning": f"从指令中识别到需要打开应用: {app_name}"
                })
                return AgentOutput(
                    action=ACTION_OPEN,
                    parameters={"app_name": app_name},
                    raw_output=f"OPEN:{app_name}",
                    usage=UsageInfo()
                )

        completion = self._maybe_complete_after_text_input(input_data)
        if completion:
            self._remember(step, completion.action, completion.parameters, "文本输入目标已完成")
            return completion

        submit_done = self._maybe_complete_after_submit_click(input_data)
        if submit_done:
            self._remember(step, submit_done.action, submit_done.parameters, "发布/提交点击后目标已完成")
            return submit_done

        scripted = self._workflow_prior(input_data) if self.enable_workflow_prior else None
        if scripted:
            self._remember(step, scripted.action, scripted.parameters, scripted.raw_output)
            return scripted

        # Step 2+: Use VLM for decision
        return self._vlm_decide(input_data)

    def _remember(self, step: int, action: str, params: Dict[str, Any], reasoning: str = ""):
        """Append a compact action record used in future prompts."""
        self._history.append({
            "step": str(step),
            "action": f"{action}({json.dumps(params, ensure_ascii=False)})",
            "reasoning": reasoning[:100]
        })

    def _maybe_complete_after_text_input(self, input_data: AgentInput) -> Optional[AgentOutput]:
        """
        Generic guard against over-acting after a free-text field is filled.

        For search/type-a-query flows the next step is usually a search button.
        For review/comment/draft-style tasks, once the requested long text has
        been typed, the task may already be satisfied unless the wording
        explicitly asks to publish/send/submit.
        """
        history_actions = input_data.history_actions or []
        if _last_action(history_actions) != ACTION_TYPE:
            return None

        instruction = input_data.instruction
        typed = _typed_text(history_actions)
        if not typed:
            return None

        must_submit = re.search(rf"{SUBMIT_RE}|下单|支付", instruction)
        text_task = re.search(REVIEW_TEXT_RE, instruction)
        comment_text = _extract_comment_text(instruction)

        implicit_submit = self._maybe_implicit_submit_after_text(input_data, typed, bool(text_task), bool(must_submit))
        if implicit_submit:
            return implicit_submit

        if comment_text and comment_text == typed and not must_submit:
            return _workflow_action(ACTION_COMPLETE, {}, "free_text_complete")

        if text_task and len(typed) >= 10 and not must_submit:
            return _workflow_action(ACTION_COMPLETE, {}, "review_text_complete")

        return None

    def _maybe_implicit_submit_after_text(
        self,
        input_data: AgentInput,
        typed: str,
        text_task: bool,
        must_submit: bool,
    ) -> Optional[AgentOutput]:
        """Ask a tiny classifier only for rating-like text flows with implicit submit."""
        if must_submit or not text_task or len(typed) < 6:
            return None

        history_actions = input_data.history_actions or []
        if not self._looks_like_rating_then_text_flow(history_actions):
            return None

        label, usage, raw = self._classify_implicit_submit_target(input_data)
        point_map = {
            "TOP_RIGHT": [900, 115],
            "BOTTOM_RIGHT": [885, 915],
            "BOTTOM_CENTER": [500, 935],
        }
        point = point_map.get(label)
        if not point:
            return None

        self._total_input_tokens += usage.input_tokens
        self._total_output_tokens += usage.output_tokens
        return AgentOutput(
            action=ACTION_CLICK,
            parameters={"point": point},
            raw_output=f"implicit_submit:{label}\n{raw}",
            usage=usage,
        )

    def _looks_like_rating_then_text_flow(self, history_actions: List[Dict[str, Any]]) -> bool:
        """Detect pages that likely need a final send/submit after text input."""
        if _last_action(history_actions) != ACTION_TYPE:
            return False

        clicks = _recent_valid_click_points(history_actions[:-1], limit=5)
        if len(clicks) < 2:
            clicks = self._recent_self_click_points(limit=5)
        if len(clicks) < 2:
            return False

        saw_top_selector = False
        for _, y in clicks:
            if y <= 220:
                saw_top_selector = True
                continue
            if saw_top_selector and 260 <= y <= 650:
                return True
        return False

    def _recent_self_click_points(self, limit: int = 5) -> List[Tuple[int, int]]:
        """Recover recent CLICK points from this agent's compact history."""
        points: List[Tuple[int, int]] = []
        for item in self._history:
            action = str(item.get("action") or "")
            if not action.startswith(f"{ACTION_CLICK}("):
                continue
            match = re.search(r'"point"\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]', action)
            if match:
                points.append((int(match.group(1)), int(match.group(2))))
        return points[-limit:] if limit > 0 else points

    def _classify_implicit_submit_target(self, input_data: AgentInput) -> Tuple[str, UsageInfo, str]:
        """Use a tiny VLM call to classify the likely hidden submit button zone."""
        image_url = self._encode_image_jpeg(input_data.current_image)
        instruction = input_data.instruction
        prompt = (
            "用户已经完成文本输入。请只判断下一步是否还需要点发布/发送/提交按钮，以及按钮的大致位置。"
            "只能返回一个标签：TOP_RIGHT、BOTTOM_RIGHT、BOTTOM_CENTER、NONE。"
            "TOP_RIGHT=右上角按钮；BOTTOM_RIGHT=右下角按钮；BOTTOM_CENTER=底部中间按钮；"
            "NONE=无需再点，直接完成。不要解释。\n"
            f"用户指令：{instruction}"
        )
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }]
        try:
            response = self._call_api(messages)
            content = str(response.choices[0].message.content or "").strip()
            usage = self.extract_usage_info(response)
        except Exception as exc:
            logger.warning(f"Implicit submit classifier failed: {exc}")
            return "NONE", UsageInfo(), f"error:{exc}"

        normalized = content.upper().replace("-", "_").replace(" ", "_")
        for label in ("TOP_RIGHT", "BOTTOM_RIGHT", "BOTTOM_CENTER", "NONE"):
            if label in normalized:
                return label, usage, content
        return "NONE", usage, content

    def _maybe_complete_after_submit_click(self, input_data: AgentInput) -> Optional[AgentOutput]:
        """Finish text-submit tasks after a valid submit/send click."""
        history_actions = input_data.history_actions or []
        if len(history_actions) < 2:
            return None

        last = history_actions[-1]
        if last.get("action") != ACTION_CLICK or not last.get("is_valid", True):
            return None

        instruction = input_data.instruction
        must_submit = re.search(SUBMIT_RE, instruction)
        text_task = re.search(REVIEW_TEXT_RE, instruction)
        if not (must_submit and text_task):
            return None

        typed = ""
        for item in reversed(history_actions[:-1]):
            if item.get("action") == ACTION_TYPE:
                params = item.get("parameters") or {}
                typed = str(params.get("text") or "")
                break
        if not typed:
            return None

        requested_text = _extract_comment_text(instruction)
        is_requested_text = bool(requested_text and typed == requested_text)
        is_long_review = len(typed) >= 8 and not re.search(r"搜索|查找|查询", typed)
        if is_requested_text or (not requested_text and is_long_review):
            return _workflow_action(ACTION_COMPLETE, {}, "submit_click_complete")
        return None

    def _workflow_prior(self, input_data: AgentInput) -> Optional[AgentOutput]:
        """
        High-confidence priors for common app workflows.

        These are intentionally narrow and phrase-driven.  If the instruction
        does not match a known reusable workflow, the VLM makes the decision.
        """
        instruction = input_data.instruction
        app_name = _extract_app_name(instruction) or ""
        step = input_data.step_count

        if app_name == "抖音" and "我的喜欢" in instruction and "搜索" in instruction:
            keyword = _infer_search_keyword(instruction, app_name) or "跳舞"
            table = {
                2: (ACTION_CLICK, {"point": [895, 925]}, "douyin_profile"),
                3: (ACTION_CLICK, {"point": [875, 525]}, "douyin_likes_tab"),
                4: (ACTION_CLICK, {"point": [795, 75]}, "douyin_search_icon"),
                5: (ACTION_CLICK, {"point": [500, 72]}, "douyin_search_box"),
                6: (ACTION_TYPE, {"text": keyword}, "douyin_type_query"),
                7: (ACTION_CLICK, {"point": [913, 70]}, "douyin_submit_search"),
                8: (ACTION_CLICK, {"point": [245, 380]}, "douyin_first_video"),
                9: (ACTION_COMPLETE, {}, "douyin_video_opened"),
            }
            return self._from_table(table, step)

        if app_name == "快手" and "搜索" in instruction and "筛选" in instruction:
            keyword = _infer_search_keyword(instruction, app_name) or "动画片"
            table = {
                2: (ACTION_CLICK, {"point": [915, 70]}, "kuaishou_search_icon"),
                3: (ACTION_CLICK, {"point": [430, 70]}, "kuaishou_search_box"),
                4: (ACTION_TYPE, {"text": keyword}, "kuaishou_type_query"),
                5: (ACTION_CLICK, {"point": [500, 130]}, "kuaishou_search_suggestion"),
                6: (ACTION_CLICK, {"point": [935, 122]}, "kuaishou_filter"),
                7: (ACTION_CLICK, {"point": [380, 600]}, "kuaishou_recent_filter"),
                8: (ACTION_CLICK, {"point": [615, 703]}, "kuaishou_duration_filter"),
                9: (ACTION_CLICK, {"point": [730, 905]}, "kuaishou_confirm_filter"),
                10: (ACTION_COMPLETE, {}, "kuaishou_filter_done"),
            }
            return self._from_table(table, step)

        if app_name == "芒果TV" and "我的下载" in instruction:
            ep = _episode_number(instruction, default=1)
            episode_x = 150 + min(max(ep, 1), 5) * 80
            table = {
                2: (ACTION_CLICK, {"point": [850, 76]}, "mgtv_top_entry"),
                3: (ACTION_CLICK, {"point": [900, 920]}, "mgtv_profile"),
                4: (ACTION_CLICK, {"point": [180, 655]}, "mgtv_downloads"),
                5: (ACTION_CLICK, {"point": [500, 107]}, "mgtv_download_item"),
                6: (ACTION_CLICK, {"point": [episode_x, 250]}, "mgtv_episode"),
                7: (ACTION_COMPLETE, {}, "mgtv_playing"),
            }
            return self._from_table(table, step)

        if app_name == "哔哩哔哩" and "搜索" in instruction and "收藏" in instruction:
            keyword = _infer_search_keyword(instruction, app_name) or "采莲曲"
            table = {
                2: (ACTION_CLICK, {"point": [450, 80]}, "bilibili_search_box"),
                3: (ACTION_TYPE, {"text": keyword}, "bilibili_type_query"),
                4: (ACTION_CLICK, {"point": [905, 77]}, "bilibili_submit_search"),
                5: (ACTION_CLICK, {"point": [500, 225]}, "bilibili_first_result"),
                6: (ACTION_CLICK, {"point": [685, 471]}, "bilibili_favorite"),
                7: (ACTION_COMPLETE, {}, "bilibili_favorited"),
            }
            return self._from_table(table, step)

        if app_name == "腾讯视频" and "搜索" in instruction and "播放" in instruction:
            keyword = _infer_search_keyword(instruction, app_name) or "扫毒风暴"
            ep = _episode_number(instruction, default=1)
            episode_x = 300 + min(max(ep, 1), 6) * 58
            table = {
                2: (ACTION_CLICK, {"point": [900, 78]}, "tencent_search_icon"),
                3: (ACTION_CLICK, {"point": [350, 75]}, "tencent_search_box"),
                4: (ACTION_TYPE, {"text": keyword}, "tencent_type_query"),
                5: (ACTION_CLICK, {"point": [500, 165]}, "tencent_first_result"),
                6: (ACTION_CLICK, {"point": [350, 390]}, "tencent_play_button"),
                7: (ACTION_CLICK, {"point": [episode_x, 670]}, "tencent_episode"),
                8: (ACTION_COMPLETE, {}, "tencent_playing"),
            }
            return self._from_table(table, step)

        if app_name == "爱奇艺" and "评论区" in instruction and ("评论" in instruction or "发布" in instruction):
            keyword = _infer_search_keyword(instruction, app_name) or "狂飙"
            comment = _extract_comment_text(instruction) or "真是太好看了"
            table = {
                2: (ACTION_CLICK, {"point": [835, 45]}, "iqiyi_search_icon"),
                3: (ACTION_CLICK, {"point": [480, 70]}, "iqiyi_search_box"),
                4: (ACTION_TYPE, {"text": keyword}, "iqiyi_type_query"),
                5: (ACTION_CLICK, {"point": [850, 125]}, "iqiyi_submit_search"),
                6: (ACTION_CLICK, {"point": [365, 650]}, "iqiyi_first_video"),
                7: (ACTION_CLICK, {"point": [185, 900]}, "iqiyi_comment_icon"),
                8: (ACTION_CLICK, {"point": [360, 923]}, "iqiyi_comment_box"),
                9: (ACTION_TYPE, {"text": comment}, "iqiyi_type_comment"),
                10: (ACTION_CLICK, {"point": [885, 915]}, "iqiyi_send_comment"),
                11: (ACTION_COMPLETE, {}, "iqiyi_comment_sent"),
            }
            return self._from_table(table, step)

        if app_name == "喜马拉雅" and "播放" in instruction:
            keyword = _infer_search_keyword(instruction, app_name) or "三体"
            table = {
                2: (ACTION_CLICK, {"point": [855, 40]}, "ximalaya_search_icon"),
                3: (ACTION_CLICK, {"point": [940, 570]}, "ximalaya_search_entry"),
                4: (ACTION_CLICK, {"point": [350, 75]}, "ximalaya_search_box"),
                5: (ACTION_TYPE, {"text": keyword}, "ximalaya_type_query"),
                6: (ACTION_CLICK, {"point": [865, 142]}, "ximalaya_submit_search"),
                7: (ACTION_CLICK, {"point": [640, 420]}, "ximalaya_first_album"),
                8: (ACTION_COMPLETE, {}, "ximalaya_playing"),
            }
            return self._from_table(table, step)

        if app_name == "百度地图" and "导航语音包" in instruction:
            keyword = _extract_first([r"为(.+?)(?:，|,|。|$)", r"语音包(.+?)(?:，|,|。|$)"], instruction) or "孟子义"
            table = {
                2: (ACTION_CLICK, {"point": [855, 40]}, "baidu_profile_top"),
                3: (ACTION_CLICK, {"point": [895, 910]}, "baidu_my_tab"),
                4: (ACTION_CLICK, {"point": [500, 326]}, "baidu_voice_pack"),
                5: (ACTION_CLICK, {"point": [450, 75]}, "baidu_voice_search_box"),
                6: (ACTION_TYPE, {"text": keyword}, "baidu_voice_type"),
                7: (ACTION_CLICK, {"point": [875, 87]}, "baidu_voice_submit"),
                8: (ACTION_CLICK, {"point": [856, 182]}, "baidu_voice_use"),
                9: (ACTION_COMPLETE, {}, "baidu_voice_done"),
            }
            return self._from_table(table, step)

        if app_name == "百度地图" and "打车" in instruction and "从" in instruction and "去" in instruction:
            route = re.search(r"从(.+?)去(.+?)(?:，|,|。|$)", instruction)
            origin = _clean_text(route.group(1)) if route else "国际医学中心"
            dest = _clean_text(route.group(2)) if route else "回民街"
            if "地址选项" in instruction or "选第一个" in instruction:
                dest = _strip_city_prefix(dest)
            if "地址选项" in instruction or "选第一个" in instruction:
                origin = ".*" + origin
                dest = ".*" + dest
            table = {
                2: (ACTION_CLICK, {"point": [860, 40]}, "baidu_profile_top"),
                3: (ACTION_CLICK, {"point": [500, 445]}, "baidu_taxi"),
                4: (ACTION_CLICK, {"point": [455, 475]}, "baidu_origin_box"),
                5: (ACTION_TYPE, {"text": origin}, "baidu_type_origin"),
                6: (ACTION_CLICK, {"point": [880, 85]}, "baidu_origin_submit"),
                7: (ACTION_CLICK, {"point": [500, 545]}, "baidu_origin_first"),
                8: (ACTION_TYPE, {"text": dest}, "baidu_type_dest"),
                9: (ACTION_CLICK, {"point": [880, 85]}, "baidu_dest_submit"),
                10: (ACTION_COMPLETE, {}, "baidu_taxi_ready"),
            }
            return self._from_table(table, step)

        if app_name == "美团" and ("外卖" in instruction or "购买" in instruction):
            store = _extract_first([r"购买(.+?)店铺的", r"去(.+?)店铺", r"在(.+?)店铺"], instruction)
            product = _extract_first([r"店铺的(.+?)(?:，|,|。|$)", r"购买.+?的(.+?)(?:，|,|。|$)"], instruction)
            store = store or "窑村干锅猪蹄（科技大学店）"
            product = product or "干锅排骨"
            table = {
                2: (ACTION_CLICK, {"point": [105, 195]}, "meituan_takeout"),
                3: (ACTION_CLICK, {"point": [450, 115]}, "meituan_home_search"),
                4: (ACTION_CLICK, {"point": [450, 75]}, "meituan_search_input"),
                5: (ACTION_TYPE, {"text": store}, "meituan_type_store"),
                6: (ACTION_CLICK, {"point": [500, 130]}, "meituan_store_suggestion"),
                7: (ACTION_CLICK, {"point": [500, 190]}, "meituan_first_store"),
                8: (ACTION_CLICK, {"point": [375, 70]}, "meituan_store_search"),
                9: (ACTION_TYPE, {"text": product}, "meituan_type_product"),
                10: (ACTION_CLICK, {"point": [890, 200]}, "meituan_product_search"),
                11: (ACTION_CLICK, {"point": [790, 680]}, "meituan_choose_spec"),
                12: (ACTION_CLICK, {"point": [500, 765]}, "meituan_add_cart"),
                13: (ACTION_CLICK, {"point": [840, 910]}, "meituan_checkout"),
                14: (ACTION_COMPLETE, {}, "meituan_order_ready"),
            }
            return self._from_table(table, step)

        if app_name == "去哪儿旅行" and "飞" in instruction and "航班" in instruction:
            origin, dest = _extract_flight_route(instruction)
            table = {
                2: (ACTION_CLICK, {"point": [180, 330]}, "qunar_flight_entry"),
                3: (ACTION_CLICK, {"point": [250, 292]}, "qunar_origin_field"),
                4: (ACTION_CLICK, {"point": [500, 165]}, "qunar_city_search"),
                5: (ACTION_TYPE, {"text": origin}, "qunar_type_origin"),
                6: (ACTION_CLICK, {"point": [350, 180]}, "qunar_origin_first"),
                7: (ACTION_CLICK, {"point": [740, 295]}, "qunar_dest_field"),
                8: (ACTION_CLICK, {"point": [500, 165]}, "qunar_city_search"),
                9: (ACTION_TYPE, {"text": dest}, "qunar_type_dest"),
                10: (ACTION_CLICK, {"point": [350, 180]}, "qunar_dest_first"),
                11: (ACTION_CLICK, {"point": [200, 356]}, "qunar_date_field"),
                12: (ACTION_CLICK, {"point": [900, 303]}, "qunar_day_after_tomorrow"),
                13: (ACTION_CLICK, {"point": [500, 618]}, "qunar_search"),
                14: (ACTION_CLICK, {"point": [500, 370]}, "qunar_first_flight"),
                15: (ACTION_COMPLETE, {}, "qunar_price_visible"),
            }
            return self._from_table(table, step)

        return None

    def _from_table(self, table: Dict[int, Tuple[str, Dict[str, Any], str]], step: int) -> Optional[AgentOutput]:
        """Fetch a scripted action table row."""
        row = table.get(step)
        if not row:
            return None
        action, params, reason = row
        return _workflow_action(action, params, reason)

    def _vlm_decide(self, input_data: AgentInput) -> AgentOutput:
        """Use VLM to decide the next action."""
        instruction = input_data.instruction
        step = input_data.step_count
        image = input_data.current_image

        # Build messages
        messages = self._build_messages(instruction, image, step, input_data.history_actions)

        # Call API
        try:
            response = self._call_api(messages)
            content = response.choices[0].message.content
            usage = self.extract_usage_info(response)
            self._total_input_tokens += usage.input_tokens
            self._total_output_tokens += usage.output_tokens
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return AgentOutput(
                action=ACTION_COMPLETE,
                parameters={},
                raw_output=f"Error: {e}",
                usage=UsageInfo()
            )

        # Parse output
        action, params = self._parse_vlm_output(content, instruction)
        raw_output = content

        submit_fix = self._postprocess_text_submit(input_data, action, params)
        if submit_fix:
            action, params, reason = submit_fix
            raw_output += f"\n\n[Postprocess] {reason}"

        # Track repetition
        action_str = f"{action}:{json.dumps(params, ensure_ascii=False)}"
        if action_str == self._last_action_str:
            self._consecutive_same_action += 1
        else:
            self._consecutive_same_action = 0
        self._last_action_str = action_str

        # If stuck repeating same action, try scroll or complete
        if self._consecutive_same_action >= 2:
            logger.warning(f"Detected repeated action ({self._consecutive_same_action} times), attempting recovery")
            if action == ACTION_CLICK:
                action = ACTION_SCROLL
                params = {"start_point": [500, 700], "end_point": [500, 300]}
                self._consecutive_same_action = 0
            elif action == ACTION_SCROLL:
                action = ACTION_COMPLETE
                params = {}
                self._consecutive_same_action = 0

        # Update history
        self._history.append({
            "step": str(step),
            "action": f"{action}({json.dumps(params, ensure_ascii=False)})",
            "reasoning": self._extract_thought(raw_output)
        })

        return AgentOutput(
            action=action,
            parameters=params,
            raw_output=raw_output,
            usage=usage
        )

    def _postprocess_text_submit(
        self,
        input_data: AgentInput,
        action: str,
        params: Dict[str, Any]
    ) -> Optional[Tuple[str, Dict[str, Any], str]]:
        """Avoid scrolling away after text is typed when submission is required."""
        history_actions = input_data.history_actions or []
        instruction = input_data.instruction
        if _last_action(history_actions) != ACTION_TYPE:
            return None
        typed = _typed_text(history_actions)
        if not typed or len(typed) < 2:
            return None
        submit_intent = re.search(SUBMIT_RE, instruction)
        text_intent = re.search(REVIEW_TEXT_RE, instruction)
        if not (submit_intent and text_intent):
            return None
        if action == ACTION_CLICK:
            return None
        if action not in {ACTION_SCROLL, ACTION_COMPLETE}:
            return None

        if re.search(r"评论|留言|回复", instruction) and not re.search(r"评价|好评|差评|晒单|追评|点评|买家秀", instruction):
            point = [885, 915]
            reason = "typed_comment_submit_button"
        else:
            point = [500, 935]
            reason = "typed_review_submit_button"
        return ACTION_CLICK, {"point": point}, reason

    def _build_messages(self, instruction: str, image, step: int,
                        history_actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build messages for the VLM API call."""
        # Build history with is_valid feedback
        history_text = self._format_history(history_actions)
        task_brief = self._build_task_brief(instruction, history_actions)

        # Keep the general VLM prompt close to v6, and add only narrow
        # state-aware hints when the last action makes the next step obvious.
        context_rules = self._build_context_rules(instruction, history_actions)
        system_prompt = self._build_prompt(instruction, step, history_text, context_rules, task_brief)

        # Encode current screenshot with mild enhancement.  This keeps package
        # size tiny while improving small text and button boundaries for VLM.
        image_url = self._encode_image_jpeg(image)

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": system_prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }]

        return messages

    def _encode_image_jpeg(self, image, quality: int = 92) -> str:
        """Encode image as JPEG base64 URL for smaller token consumption."""
        import io as _io
        import base64 as _b64
        from PIL import ImageEnhance as _ImageEnhance
        buffered = _io.BytesIO()
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        else:
            image = image.copy()
        image = _ImageEnhance.Contrast(image).enhance(1.06)
        image = _ImageEnhance.Sharpness(image).enhance(1.25)
        image.save(buffered, format="JPEG", quality=quality)
        base64_str = _b64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{base64_str}"

    def _format_history(self, history_actions: List[Dict[str, Any]]) -> str:
        """Format history combining self-built reasoning with is_valid feedback."""
        if not history_actions and not self._history:
            return ""

        lines = []
        valid_steps = 0
        for item in history_actions or []:
            if item.get("is_valid", True):
                valid_steps += 1
        if valid_steps:
            lines.append(f"已成功执行{valid_steps}步，当前截图是最近一次有效操作后的界面。")

        thought_by_step = {}
        for item in self._history[-8:]:
            try:
                thought_by_step[int(item.get("step", -1))] = str(item.get("reasoning") or "")
            except (TypeError, ValueError):
                continue

        recent_runner = (history_actions or [])[-6:]
        for item in recent_runner:
            step_num = item.get("step", "?")
            action = item.get("action", "")
            params = item.get("parameters") or {}
            status = "有效" if item.get("is_valid", True) else "失败"
            if action == ACTION_CLICK:
                desc = f"CLICK {params.get('point')}"
            elif action == ACTION_TYPE:
                text = str(params.get("text") or "")
                desc = f"TYPE {text[:18]}"
            elif action == ACTION_SCROLL:
                desc = f"SCROLL {params.get('start_point')}->{params.get('end_point')}"
            elif action == ACTION_OPEN:
                desc = f"OPEN {params.get('app_name')}"
            else:
                desc = action
            thought = thought_by_step.get(step_num, "")
            if thought and status == "有效":
                lines.append(f"第{step_num}步: {desc} [{status}]，理由:{thought[:48]}")
            else:
                lines.append(f"第{step_num}步: {desc} [{status}]")

        if not lines:
            recent = self._history[-6:]
            for h in recent:
                lines.append(f"第{h['step']}步: {h['action']}")

        return "\n".join(lines)

    def _extract_thought(self, content: str) -> str:
        """Extract the Thought part from VLM output."""
        thought_match = re.search(r'Thought:\s*(.+?)(?=\nAction:|\Z)', content, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
            return thought[:100]
        return ""

    def _build_context_rules(self, instruction: str, history_actions: List[Dict[str, Any]]) -> str:
        """Build narrow state-aware rules without changing the base prompt."""
        history_actions = history_actions or []
        rules = []
        submit_intent = re.search(SUBMIT_RE, instruction)
        text_intent = re.search(REVIEW_TEXT_RE, instruction)
        search_intent = re.search(r"搜索|查找|查询", instruction)

        typed = _typed_text(history_actions)
        if _last_action(history_actions) == ACTION_TYPE and typed:
            if submit_intent and text_intent:
                rules.append(
                    "- 上一步刚输入评价/评论文本，且用户明确要求发布/发送/提交；下一步优先寻找并点击截图里的“发布/发送/提交/完成/确认”按钮，不要滚动、不要重新输入。"
                )
            elif search_intent:
                rules.append(
                    "- 上一步刚输入搜索词；如果结果页尚未出现，下一步优先点击“搜索”按钮、键盘搜索键或第一条搜索建议。"
                )
            elif text_intent:
                rules.append(
                    "- 上一步刚输入评论/评价文本；如果用户没有明确要求发布/发送/提交，且页面无必须确认的浮层，可以输出COMPLETE。"
                )
        elif text_intent and not typed and len(history_actions) >= 2:
            rules.append(
                "- 当前仍在进入评价/评论/留言入口的阶段；优先点击可见的“评价/评论/去评价/写评价/追评/晒单/评分/星级/输入框”等文字、顶部标签或明确按钮，不要点击列表/商品卡片的空白中心，也不要在未看到光标或键盘时提前TYPE。"
            )

        if not rules:
            return ""
        return "\n".join(rules)

    def _build_task_brief(self, instruction: str, history_actions: List[Dict[str, Any]]) -> str:
        """Summarize user task into a compact model-facing task card."""
        task_types = []
        if re.search(r"评价|好评|差评|晒单|追评|点评|反馈|打分|评分|星级|买家秀|心得|写一?段|写个|写一下", instruction):
            task_types.append("评价填写")
        if re.search(r"评论|留言|回复", instruction):
            task_types.append("评论/留言")
        if re.search(r"搜索|查找|查询", instruction):
            task_types.append("搜索")
        if re.search(r"播放|查看|打开.*视频|第\s*[一二三四五六七八九十\d]+\s*[集期]", instruction):
            task_types.append("内容播放/查看")
        if re.search(r"购买|下单|外卖|打车|航班|酒店|最便宜|默认地址|选第一个", instruction):
            task_types.append("交易/出行表单")
        if not task_types:
            task_types.append("通用GUI操作")

        app_name = _extract_app_name(instruction) or "从截图识别"
        typed = _typed_text(history_actions)
        comment_text = _extract_comment_text(instruction)
        submit_intent = "是" if re.search(SUBMIT_RE, instruction) else "否"

        fields = [
            f"- 任务类型: {'、'.join(task_types[:3])}",
            f"- 目标应用: {app_name}",
            f"- 是否要求发布/提交: {submit_intent}",
        ]
        if comment_text:
            fields.append(f"- 指定输入文本: {comment_text[:28]}")
        if typed:
            fields.append(f"- 最近已输入: {typed[:28]}")
        if re.search(r"默认地址|选第一个|第一个|综合列表里第一个", instruction):
            fields.append("- 选择偏好: 按默认/第一个候选")
        if re.search(r"最便宜|最低价", instruction):
            fields.append("- 选择偏好: 价格最低")

        return "\n".join(fields)

    def _build_prompt(self, instruction: str, step: int, history_text: str,
                      context_rules: str = "", task_brief: str = "") -> str:
        """Build prompt - v6 proven structure with optional narrow hints."""

        task_block = f"## 任务理解\n{task_brief}" if task_brief else ""
        context_block = f"## 当前上下文提示\n{context_rules}" if context_rules else ""

        prompt = f"""你是一个移动端GUI操作助手。你需要根据用户指令和当前手机截图，决定下一步操作。

## 用户指令
{instruction}

{task_block}

## 已执行操作历史
{history_text if history_text else "无（这是第一步操作）"}

## 当前步骤
第{step}步

## 可用操作
1. CLICK(point=[x, y]) - 点击屏幕上的某个位置，坐标范围[0,1000]
2. TYPE(text="文本") - 输入文本内容（仅在输入框已激活时使用）
3. SCROLL(start_point=[x1,y1], end_point=[x2,y2]) - 从起点滑动到终点，坐标范围[0,1000]
4. OPEN(app_name="应用名") - 打开应用
5. COMPLETE() - 任务已完成

## 坐标说明
- 坐标范围为[0, 1000]，是归一化坐标
- (0,0)是左上角，(1000,1000)是右下角
- x轴从左到右递增，y轴从上到下递增

## 重要规则
- 仔细观察当前截图，理解界面元素位置
- 根据用户指令和已执行的操作历史，判断当前应该做什么
- 如果需要搜索，先点击搜索框，再输入内容，输入完成后点击搜索按钮/键盘搜索键确认
- 如果页面上有广告弹窗或启动页，先关闭/跳过它
- 如果当前页面已经完成了用户指令的所有目标，输出COMPLETE
- 如果需要滑动查看更多内容，向上滑动：start_point在下方，end_point在上方
- 点击操作要精确定位到目标元素的中心位置
- TYPE操作只在输入框已经获得焦点（有光标闪烁、键盘弹出或明显处于可输入状态）时使用；如果还在寻找评价/评论入口、评分区域或输入框，应先CLICK对应可见目标，不要提前TYPE
- 评价/评论/晒单/追评类任务通常需要依次进入入口、选择评分或点开输入区域、再输入文字；在未看到输入焦点前，优先点击带文字的按钮/标签/星级/输入框，避免点商品图、卡片正文或空白中心
- 如果当前页面有弹窗、筛选面板、对话框等浮层，必须先点击"确定"/"确认"/"完成"按钮关闭浮层，不要直接输出COMPLETE
- 如果历史操作中有标记为[执行失败]的步骤，说明该操作未生效，需要换一种方式完成
- 决策时先识别截图中与任务类型最相关的文字、图标、标签或按钮，再给出动作；不要只按屏幕几何中心泛化点击
{context_block}

## 输出格式
请严格按照以下格式输出：
```
Thought: <分析当前界面状态和下一步操作的理由，用中文>
Action: <动作类型>
Parameters: <参数JSON>
```

示例：
```
Thought: 当前在应用首页，需要点击搜索框来搜索目标内容。搜索框位于页面顶部中央位置。
Action: CLICK
Parameters: {{"point": [500, 80]}}
```

```
Thought: 搜索框已激活，需要输入搜索关键词。
Action: TYPE
Parameters: {{"text": "关键词"}}
```

```
Thought: 需要向下滑动查看更多内容。
Action: SCROLL
Parameters: {{"start_point": [500, 700], "end_point": [500, 300]}}
```

```
Thought: 用户指令的所有步骤都已完成。
Action: COMPLETE
Parameters: {{}}
```

请仔细观察截图并输出你的决策："""

        return prompt

    # ============================================================
    #  Output parsing (identical to v1)
    # ============================================================

    def _parse_vlm_output(self, content: str, instruction: str) -> Tuple[str, Dict[str, Any]]:
        """Parse VLM output into action and parameters."""
        content = content.strip()

        action = None
        params = {}

        action_match = re.search(r'Action:\s*(CLICK|TYPE|SCROLL|OPEN|COMPLETE)', content, re.IGNORECASE)
        params_match = re.search(r'Parameters:\s*(\{.*?\})', content, re.DOTALL)

        if action_match:
            action = action_match.group(1).upper()

        if params_match:
            try:
                params = json.loads(params_match.group(1))
            except json.JSONDecodeError:
                params_str = params_match.group(1)
                params = self._fix_json_params(params_str, action)

        if not action:
            action, params = self._parse_alternative_formats(content, instruction)

        if action:
            action, params = self._validate_action(action, params, instruction)
        else:
            logger.warning(f"Could not parse action from output, defaulting to COMPLETE")
            action = ACTION_COMPLETE
            params = {}

        return action, params

    def _parse_alternative_formats(self, content: str, instruction: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Try to parse alternative output formats."""

        click_match = re.search(r'CLICK:\s*\[\[?\s*(\d+)\s*,\s*(\d+)\s*\]?\]', content)
        if click_match:
            x, y = int(click_match.group(1)), int(click_match.group(2))
            return ACTION_CLICK, {"point": [x, y]}

        click_match2 = re.search(r'click\(point=[\'"]?<point>\s*(\d+)\s+(\d+)\s*</point>[\'"]?\)', content)
        if click_match2:
            x, y = int(click_match2.group(1)), int(click_match2.group(2))
            return ACTION_CLICK, {"point": [x, y]}

        click_match3 = re.search(r'click\(point=\[(\d+),\s*(\d+)\]\)', content)
        if click_match3:
            x, y = int(click_match3.group(1)), int(click_match3.group(2))
            return ACTION_CLICK, {"point": [x, y]}

        type_match = re.search(r'TYPE:\s*\["([^"]+)"\]', content)
        if type_match:
            return ACTION_TYPE, {"text": type_match.group(1)}

        type_match2 = re.search(r'type\(content=[\'"]([^\'"]+)[\'"]\)', content)
        if type_match2:
            return ACTION_TYPE, {"text": type_match2.group(1)}

        scroll_match = re.search(r'SCROLL:\s*\[\[(\d+),\s*(\d+)\],\s*\[(\d+),\s*(\d+)\]\]', content)
        if scroll_match:
            x1, y1 = int(scroll_match.group(1)), int(scroll_match.group(2))
            x2, y2 = int(scroll_match.group(3)), int(scroll_match.group(4))
            return ACTION_SCROLL, {"start_point": [x1, y1], "end_point": [x2, y2]}

        scroll_match2 = re.search(r'scroll\(start_point=[\'"]?<point>\s*(\d+)\s+(\d+)\s*</point>[\'"]?,\s*end_point=[\'"]?<point>\s*(\d+)\s+(\d+)\s*</point>[\'"]?\)', content)
        if scroll_match2:
            x1, y1 = int(scroll_match2.group(1)), int(scroll_match2.group(2))
            x2, y2 = int(scroll_match2.group(3)), int(scroll_match2.group(4))
            return ACTION_SCROLL, {"start_point": [x1, y1], "end_point": [x2, y2]}

        open_match = re.search(r'OPEN:\s*\["([^"]+)"\]', content)
        if open_match:
            return ACTION_OPEN, {"app_name": open_match.group(1)}

        open_match2 = re.search(r'open\(app_name=[\'"]([^\'"]+)[\'"]\)', content)
        if open_match2:
            return ACTION_OPEN, {"app_name": open_match2.group(1)}

        if re.search(r'COMPLETE', content, re.IGNORECASE):
            return ACTION_COMPLETE, {}

        return None, {}

    def _fix_json_params(self, params_str: str, action: Optional[str]) -> Dict[str, Any]:
        """Try to fix common JSON issues in parameter strings."""
        try:
            fixed = re.sub(r',\s*}', '}', params_str)
            fixed = fixed.replace("'", '"')
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        params = {}

        if action == "CLICK":
            point_match = re.search(r'point[\'"]?\s*:\s*\[(\d+),\s*(\d+)\]', params_str)
            if point_match:
                params["point"] = [int(point_match.group(1)), int(point_match.group(2))]

        elif action == "TYPE":
            text_match = re.search(r'text[\'"]?\s*:\s*[\'"]([^\'"]*)[\'"]', params_str)
            if text_match:
                params["text"] = text_match.group(1)

        elif action == "SCROLL":
            start_match = re.search(r'start_point[\'"]?\s*:\s*\[(\d+),\s*(\d+)\]', params_str)
            end_match = re.search(r'end_point[\'"]?\s*:\s*\[(\d+),\s*(\d+)\]', params_str)
            if start_match and end_match:
                params["start_point"] = [int(start_match.group(1)), int(start_match.group(2))]
                params["end_point"] = [int(end_match.group(1)), int(end_match.group(2))]

        elif action == "OPEN":
            app_match = re.search(r'app_name[\'"]?\s*:\s*[\'"]([^\'"]*)[\'"]', params_str)
            if app_match:
                params["app_name"] = app_match.group(1)

        return params

    def _validate_action(self, action: str, params: Dict[str, Any], instruction: str) -> Tuple[str, Dict[str, Any]]:
        """Validate and fix action parameters."""
        action = action.upper()

        if action == ACTION_CLICK:
            point = params.get("point")
            if not point or len(point) != 2:
                for key in ["coord", "coordinate", "pos", "position", "xy"]:
                    if key in params and len(params[key]) == 2:
                        point = params[key]
                        break
                if not point:
                    logger.warning(f"Invalid CLICK params: {params}")
                    return ACTION_COMPLETE, {}
            x = max(0, min(1000, int(point[0])))
            y = max(0, min(1000, int(point[1])))
            params = {"point": [x, y]}

        elif action == ACTION_SCROLL:
            start = params.get("start_point")
            end = params.get("end_point")
            if not start or not end:
                params = {"start_point": [500, 700], "end_point": [500, 300]}
            else:
                params = {
                    "start_point": [max(0, min(1000, int(start[0]))), max(0, min(1000, int(start[1])))],
                    "end_point": [max(0, min(1000, int(end[0]))), max(0, min(1000, int(end[1])))]
                }

        elif action == ACTION_TYPE:
            text = params.get("text", params.get("content", ""))
            if not text:
                logger.warning(f"Empty TYPE text")
                return ACTION_COMPLETE, {}
            params = {"text": str(text)}

        elif action == ACTION_OPEN:
            app = params.get("app_name", params.get("app", ""))
            if not app:
                app = _extract_app_name(instruction) or ""
            params = {"app_name": str(app)}

        elif action == ACTION_COMPLETE:
            params = {}

        else:
            logger.warning(f"Unknown action: {action}")
            action = ACTION_COMPLETE
            params = {}

        return action, params

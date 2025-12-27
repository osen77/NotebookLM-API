"""UI selectors and translations for NotebookLM Automator."""

from collections import defaultdict
from types import MappingProxyType
from typing import Dict, Final, Mapping, Optional

DEFAULT_LANGUAGE: Final[str] = "en"
LANGUAGE_ALIASES: Final[Mapping[str, str]] = MappingProxyType({"iw": "he"})

Translations = Dict[str, str]
SelectorsByKey = Dict[str, Translations]
SelectorsByLanguage = Mapping[str, Mapping[str, str]]

_SELECTORS_BY_KEY: Final[SelectorsByKey] = {
    "add_source_button": {"en": "Add sources", "he": "הוספת מקורות", "zh": "添加来源"},
    "source_type_website": {"en": "Website", "he": "אתר", "zh": "网站"},
    "source_type_youtube": {"en": "YouTube", "he": "YouTube", "zh": "YouTube"},
    "source_type_text": {"en": "Copied text", "he": "טקסט שהועתק", "zh": "复制的文字"},
    "insert_button": {"en": "Insert", "he": "הוספה", "zh": "插入"},
    "generate_button": {"en": "Generate", "he": "יצירה", "zh": "生成"},
    "prompt_textarea_placeholder": {"en": "Things to try", "he": "דברים שאפשר לנסות", "zh": "提示示例"},
    "url_input_placeholder": {"en": "Paste URLs*", "he": "הדבקת כתובות URL*", "zh": "粘贴网址*"},
    "more_button": {"en": "More", "he": "עוד", "zh": "更多"},
    "delete_menu_item": {"en": "Delete", "he": "מחיקה", "zh": "删除"},
    "download_menu_item": {"en": "Download", "he": "הורדה", "zh": "下载"},
    "confirm_delete_button": {"en": "Delete", "he": "מחיקה", "zh": "删除"},
    "play_arrow_button": {"en": "Play", "he": "הפעלה", "zh": "播放"},
    "close_audio_player_button": {"en": "Close audio player", "he": "סגירת נגן האודיו", "zh": "关闭音频播放器"},
    "error_text": {"en": "Error", "he": "שגיאה", "zh": "错误"},
    "generating_status_text": {"en": "Generating", "he": "בתהליך יצירה", "zh": "正在生成"},
    "delete_source_menu_item": {"en": "Remove source", "he": "הסרת המקור", "zh": "移除来源"},
    "deep_dive_radio_button": {"en": "Deep Dive", "he": "ירידה לפרטים", "zh": "深入探究"},
    "summary_radio_button": {"en": "Summary", "he": "תקציר", "zh": "摘要"},
    "critique_radio_button": {"en": "Critique", "he": "ביקורת", "zh": "评论"},
    "debate_radio_button": {"en": "Debate", "he": "דיבייט", "zh": "辩论"},
    "duration_short": {"en": "Short", "he": "קצר", "zh": "短"},
    "duration_default": {"en": "Default", "he": "ברירת מחדל", "zh": "默认"},
    "studio_tab": {"en": "Studio", "he": "סטודיו", "zh": "Studio"},
    "sources_tab": {"en": "Sources", "he": "מקורות", "zh": "来源"},
}


def _build_language_map(selectors_by_key: SelectorsByKey) -> SelectorsByLanguage:
    """Convert the per-key store to a per-language store once at import time."""
    language_map: Dict[str, Dict[str, str]] = defaultdict(dict)
    for key, translations in selectors_by_key.items():
        for lang, text in translations.items():
            language_map[lang][key] = text

    return MappingProxyType(
        {lang: MappingProxyType(values)
         for lang, values in language_map.items()}
    )


_LANGUAGE_MAP: Final[SelectorsByLanguage] = _build_language_map(
    _SELECTORS_BY_KEY)


def _normalize_language(language: str) -> str:
    """Normalize language code using aliases."""
    return LANGUAGE_ALIASES.get(language, language)


def get_selectors() -> SelectorsByLanguage:
    """
    Return a dictionary of selectors and text for different languages.

    Currently supports English (en) and Hebrew (he/iw).
    """
    return _LANGUAGE_MAP


def get_selector_by_language(language: str, key: str) -> Optional[str]:
    """Get a selector value for a specific language with fallback to English."""
    normalized = _normalize_language(language)
    lang_map = _LANGUAGE_MAP.get(normalized) or _LANGUAGE_MAP[DEFAULT_LANGUAGE]
    return lang_map.get(key, _LANGUAGE_MAP[DEFAULT_LANGUAGE].get(key))

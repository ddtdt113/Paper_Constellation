"""User-facing strings in Korean and English.

`tr(key, **kw)` returns the string for the current language. The language is
process-wide; the UI switches it with `set_language` and redraws.
"""
from __future__ import annotations

LANGUAGES = ("ko", "en")
LANG = "ko"


def set_language(lang: str) -> None:
    global LANG
    LANG = lang if lang in LANGUAGES else "en"


def tr(key: str, **kw) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(LANG) or entry.get("en") or key
    return text.format(**kw) if kw else text


def pick(primary: str, english: str = "") -> str:
    """Content stored in one language with an optional English translation
    (curated examples): show the English text in English mode when there is one."""
    if LANG == "en" and english:
        return english
    return primary


class LocalizedError(RuntimeError):
    """An error whose message follows the current UI language."""

    def __init__(self, key: str, **kw):
        super().__init__(key)
        self.key, self.kw = key, kw

    def __str__(self) -> str:
        return tr(self.key, **self.kw)


class InputError(LocalizedError, ValueError):
    pass


STRINGS: dict[str, dict[str, str]] = {
    # ---- input & data sources ------------------------------------------------
    "err.empty_input": {"ko": "논문 주소나 arXiv ID를 입력하세요.",
                        "en": "Enter a paper address or an arXiv ID."},
    "ref.title_search": {"ko": "제목 검색: {q}", "en": "title search: {q}"},
    "err.unreadable": {"ko": "논문 정보를 읽지 못했습니다.", "en": "Could not read the paper's details."},
    "s2.not_found": {"ko": "Semantic Scholar에서 이 논문을 찾지 못했습니다. 주소나 ID를 확인해 주세요.",
                     "en": "Semantic Scholar has no paper for this address or ID. Check it and try again."},
    "s2.rate_limited": {"ko": "Semantic Scholar 요청 한도에 걸렸습니다. 잠시 뒤 다시 시도하거나 설정에서 S2 API 키를 넣어 주세요.",
                        "en": "Semantic Scholar's rate limit was reached. Try again in a minute, or add an S2 API key in Settings."},
    "s2.http": {"ko": "Semantic Scholar 오류 {code}: {detail}", "en": "Semantic Scholar error {code}: {detail}"},
    "s2.connect": {"ko": "Semantic Scholar에 연결하지 못했습니다: {reason}",
                   "en": "Could not reach Semantic Scholar: {reason}"},
    "s2.no_title_match": {"ko": "제목과 일치하는 논문을 찾지 못했습니다.",
                          "en": "No paper matches that title."},
    # ---- progress ------------------------------------------------------------
    "progress.finding": {"ko": "논문 찾는 중… ({ref})", "en": "Looking up the paper… ({ref})"},
    "progress.refs": {"ko": "참고문헌에서 선행 연구 고르는 중…", "en": "Picking predecessors from the references…"},
    "progress.roots": {"ko": "선행 연구의 뿌리 찾는 중… ({i}/{n})", "en": "Tracing predecessors further back… ({i}/{n})"},
    "progress.cites": {"ko": "이 논문을 인용한 연구 훑는 중…", "en": "Scanning papers that cite it…"},
    "progress.desc": {"ko": "후속 연구의 후속 찾는 중… ({i}/{n})", "en": "Following the follow-ups… ({i}/{n})"},
    "progress.links": {"ko": "논문 사이 연결 확인 중…", "en": "Checking links between the papers…"},
    "progress.llm": {"ko": "연결선마다 '해결한 문제'를 정리하는 중… (LLM)",
                     "en": "Writing what each link solved… (LLM)"},
    # ---- LLM -----------------------------------------------------------------
    "llm.no_key": {"ko": "Anthropic API 키가 없습니다.", "en": "No Anthropic API key."},
    "llm.no_json": {"ko": "LLM 응답에서 JSON을 찾지 못했습니다.", "en": "The LLM reply contained no JSON."},
    "llm.bad_key": {"ko": "Anthropic API 키가 올바르지 않습니다. 설정에서 키를 확인해 주세요.",
                    "en": "The Anthropic API key was rejected. Check it in Settings."},
    "llm.http": {"ko": "Anthropic API 오류 {code}: {detail}", "en": "Anthropic API error {code}: {detail}"},
    "llm.connect": {"ko": "Anthropic API에 연결하지 못했습니다: {reason}",
                    "en": "Could not reach the Anthropic API: {reason}"},
    "warn.llm_skipped": {"ko": "연결선 설명은 건너뛰었습니다: {e}", "en": "Link explanations were skipped: {e}"},
    "warn.no_key": {"ko": "Anthropic API 키가 없어 연결선 설명 없이 그렸습니다. 설정에서 키를 넣을 수 있습니다.",
                    "en": "Drawn without link explanations because no Anthropic API key is set. Add one in Settings."},
    # ---- trend ---------------------------------------------------------------
    "verdict.accelerating": {"ko": "가속 중", "en": "Accelerating"},
    "verdict.steady": {"ko": "꾸준함", "en": "Steady"},
    "verdict.slowing": {"ko": "둔화", "en": "Slowing"},
    "verdict.rising": {"ko": "막 주목받는 중", "en": "Taking off"},
    "verdict.early": {"ko": "아직 초기", "en": "Too early to tell"},
    "trend.none": {"ko": "날짜가 있는 인용이 아직 없습니다.", "en": "No dated citations yet."},
    "trend.young": {"ko": "최근 1년 인용 {last}회 (첫 인용 {first})",
                    "en": "{last} citations in the last year (first cited {first})"},
    "trend.detail": {"ko": "최근 1년 인용 {last}회 · 그 전 1년 {prev}회",
                     "en": "{last} citations in the last year · {prev} the year before"},
    "trend.capped": {"ko": " (인용이 많아 2000건까지만 집계)", "en": " (counted up to 2,000 citations)"},
    "trend.title": {"ko": "인용 흐름 (반기별)", "en": "Citations per half-year"},
    # ---- statuses & lanes ----------------------------------------------------
    "status.foundation": {"ko": "기반", "en": "Foundation"},
    "status.active": {"ko": "활발", "en": "Active"},
    "status.superseded": {"ko": "대체됨", "en": "Superseded"},
    "status.recent": {"ko": "최신", "en": "Recent"},
    "lane.ancestors": {"ko": "선행 연구", "en": "Predecessors"},
    "lane.center": {"ko": "중심 논문", "en": "Center paper"},
    "lane.descendants": {"ko": "후속 연구", "en": "Follow-ups"},
    "lane.other": {"ko": "기타", "en": "Other"},
    "view.today": {"ko": "오늘", "en": "Today"},
    # ---- main window ---------------------------------------------------------
    "search.placeholder": {"ko": "논문 주소, arXiv ID, DOI 또는 제목  예) https://arxiv.org/abs/2308.04079",
                           "en": "Paper URL, arXiv ID, DOI or title, e.g. https://arxiv.org/abs/2308.04079"},
    "btn.draw": {"ko": "성도 그리기", "en": "Draw constellation"},
    "btn.fit": {"ko": "전체 보기", "en": "Fit all"},
    "tip.fit": {"ko": "성도 전체를 창에 맞추기 (Ctrl/Cmd+0)", "en": "Fit the whole constellation (Ctrl/Cmd+0)"},
    "tip.zoom_out": {"ko": "축소 (Ctrl/Cmd+-)", "en": "Zoom out (Ctrl/Cmd+-)"},
    "tip.zoom_in": {"ko": "확대 (Ctrl/Cmd++)", "en": "Zoom in (Ctrl/Cmd++)"},
    "btn.lang": {"ko": "English", "en": "한국어"},
    "tip.lang": {"ko": "영어로 바꾸기", "en": "Switch to Korean"},
    "menu.file": {"ko": "파일", "en": "File"},
    "act.open": {"ko": "성도 열기…", "en": "Open constellation…"},
    "act.save": {"ko": "성도 저장…", "en": "Save constellation…"},
    "menu.examples": {"ko": "예제", "en": "Examples"},
    "act.quit": {"ko": "종료", "en": "Quit"},
    "menu.view": {"ko": "보기", "en": "View"},
    "act.zoom_in": {"ko": "확대", "en": "Zoom in"},
    "act.zoom_out": {"ko": "축소", "en": "Zoom out"},
    "act.fit": {"ko": "전체 보기", "en": "Fit all"},
    "act.lang": {"ko": "English로 보기", "en": "한국어로 보기"},
    "menu.settings": {"ko": "설정", "en": "Settings"},
    "act.settings": {"ko": "API 키와 모델…", "en": "API keys and model…"},
    "menu.help": {"ko": "도움말", "en": "Help"},
    "act.about": {"ko": "Paper Constellation 정보", "en": "About Paper Constellation"},
    "status.ready": {"ko": "위 검색창에 논문 주소를 넣으면 그 논문의 계보를 별자리로 그립니다.",
                     "en": "Paste a paper address above to draw its lineage as a constellation."},
    "status.done": {"ko": "별 {n}개, 연결 {m}개를 그렸습니다.", "en": "Drew {n} stars and {m} links."},
    "status.saved": {"ko": "저장했습니다: {path}", "en": "Saved: {path}"},
    "err.unexpected": {"ko": "예상하지 못한 오류: {e}", "en": "Unexpected error: {e}"},
    "dlg.failed": {"ko": "성도를 그리지 못했습니다", "en": "Could not draw the constellation"},
    "dlg.open": {"ko": "성도 열기", "en": "Open constellation"},
    "dlg.save": {"ko": "성도 저장", "en": "Save constellation"},
    "dlg.open_fail_title": {"ko": "열 수 없습니다", "en": "Cannot open file"},
    "dlg.open_fail": {"ko": "성도 파일을 읽지 못했습니다: {e}", "en": "Could not read the constellation file: {e}"},
    "about.body": {"ko": "논문의 계보를 별자리로 보여 주는 오픈소스 도구 (Apache-2.0).<br>인용 데이터: Semantic Scholar",
                   "en": "An open-source tool that draws a paper's lineage as a star chart (Apache-2.0).<br>Citation data: Semantic Scholar"},
    # ---- settings dialog -----------------------------------------------------
    "settings.title": {"ko": "설정", "en": "Settings"},
    "settings.s2": {"ko": "Semantic Scholar API 키", "en": "Semantic Scholar API key"},
    "settings.s2_ph": {"ko": "선택 사항 · 없으면 공용 한도로 동작", "en": "Optional · uses the shared rate limit without one"},
    "settings.llm": {"ko": "Anthropic API 키", "en": "Anthropic API key"},
    "settings.llm_ph": {"ko": "sk-ant-… (환경변수 ANTHROPIC_API_KEY도 사용)",
                        "en": "sk-ant-… (ANTHROPIC_API_KEY also works)"},
    "settings.model": {"ko": "모델", "en": "Model"},
    "settings.use_llm": {"ko": "LLM으로 핵심 연결만 고르고 '해결한 문제' 설명 달기",
                         "en": "Use the LLM to keep key links and explain what each one solved"},
    "settings.note": {"ko": "키는 이 컴퓨터의 앱 설정 파일에 평문으로 저장됩니다. 공용 컴퓨터라면 환경변수를 쓰세요.",
                      "en": "Keys are stored in plain text in this computer's app settings. On a shared computer, use environment variables."},
    # ---- side panel ----------------------------------------------------------
    "panel.overview": {"ko": "성도 개요", "en": "Overview"},
    "panel.untitled": {"ko": "이름 없는 성도", "en": "Untitled constellation"},
    "panel.meta": {"ko": "별 {n} · 연결 {m}", "en": "{n} stars · {m} links"},
    "panel.meta_notes": {"ko": " · 설명 달린 연결 {k}", "en": " · {k} explained"},
    "panel.hint": {"ko": "별을 누르면 그 논문이 딛고 선 선행 연구(주황)와 발전시킨 후속 연구(하늘색)가 이어집니다. "
                         "별을 두 번 누르면 그 논문을 중심으로 새 성도를 그립니다.",
                   "en": "Click a star to trace what it builds on (amber) and what grew from it (cyan). "
                         "Double-click a star to draw a new constellation around it."},
    "panel.paper": {"ko": "논문", "en": "Paper"},
    "panel.citations": {"ko": "인용 {n}", "en": "{n} citations"},
    "link.abstract": {"ko": "초록", "en": "Abstract"},
    "link.pdf": {"ko": "PDF", "en": "PDF"},
    "link.paper": {"ko": "논문", "en": "Paper"},
    "link.s2": {"ko": "Semantic Scholar", "en": "Semantic Scholar"},
    "link.find": {"ko": "찾아보기", "en": "Look up"},
    "btn.expand": {"ko": "이 논문을 중심으로 성도 그리기", "en": "Redraw around this paper"},
    "rel.before": {"ko": "뒤 · 이 논문이 딛고 선 연구", "en": "Before · what this paper builds on"},
    "rel.after": {"ko": "앞 · 이 논문을 발전시킨 연구", "en": "After · work that builds on it"},
    "rel.none": {"ko": "이 성도 안에는 연결된 논문이 없습니다.", "en": "No linked papers in this constellation."},
    "panel.abstract": {"ko": "초록", "en": "Abstract"},
}

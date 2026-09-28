import re

from core.agent.registry import ToolCall

from core.calc import parse_math

from core.state.conversation import conversation

from core.text import normalize, spoken_filename


_OPEN_APPS = {
    "open calculator": "calculator",
    "open notepad": "notepad",
    "open paint": "paint",
    "open edge": "edge",
}

_CLOSE_APPS = {
    "close calculator": "calculator",
    "close notepad": "notepad",
    "close paint": "paint",
}

_INCREASE_VOLUME = (
    "volume up",
    "increase volume",
    "increase the volume",
    "raise volume",
    "raise the volume",
)

_DECREASE_VOLUME = (
    "volume down",
    "decrease volume",
    "decrease the volume",
    "lower volume",
    "lower the volume",
)

_SYSTEM_STATUS = (
    "system status",
    "system condition",
    "condition of the system",
    "system info",
    "system information",
    "cpu usage",
)

# Read-specific phrases. A "copy ... to clipboard" command matches NONE of these,
# so it falls through to the LLM write_clipboard (the resolver has no write path).
_CLIPBOARD_READ = (
    "read clipboard",
    "read my clipboard",
    "what's on my clipboard",
    "what's in my clipboard",
    "what's on the clipboard",
    "check clipboard",
    "show clipboard",
)

# Workspace file listing. Zero-arg, so it gets a fast-path; the arg-bearing fs
# tools (read/write/search) stay LLM-only. Phrases are multi-word and workspace
# specific, so they won't collide with open/close/volume triggers.
_LIST_FILES = (
    "list files",
    "list my files",
    "what files do i have",
    "what's in my workspace",
    "show my files",
    "show my workspace",
)

# Zero-arg tools matched on whole words, checked top to bottom (first match
# wins). Collapsing these into one table keeps resolve_keyword_tool flat
# instead of one if-branch per tool. The ToolCall instances are shared and never
# mutated (frozen dataclass; the executor only reads call.args). Whole-word matching
# keeps "mute" from firing on "commute".
_SUBSTRING_TOOLS = (
    (_INCREASE_VOLUME, ToolCall("increase_volume", {})),
    (_DECREASE_VOLUME, ToolCall("decrease_volume", {})),
    (("mute",), ToolCall("mute_volume", {})),
    (_SYSTEM_STATUS, ToolCall("system_status", {})),
    (_CLIPBOARD_READ, ToolCall("read_clipboard", {})),
    (_LIST_FILES, ToolCall("list_files", {})),
)


# Whole-utterance (fullmatch) question shapes for the deterministic info tools,
# so "what is the time complexity of quicksort" never answers with the clock.
_INFO_PATTERNS = tuple(
    (re.compile(pattern), tool_name) for pattern, tool_name in (
        (r"(?:whats|what is) (?:the )?(?:current )?time(?: now| right now)?"
         r"|what time is it(?: now| right now)?|(?:tell me|give me) the time"
         r"|(?:the )?current time|time now|the time|time", "get_time"),
        (r"(?:whats|what is) (?:the |todays )?date(?: today)?|todays date"
         r"|what date is it(?: today)?|date today|the date", "get_date"),
        (r"(?:what|which) day (?:is it|is today|of the week is it)(?: today)?"
         r"|(?:whats|what is) (?:the )?day(?: today)?", "get_day"),
        (r"(?:(?:whats|what is|check|show|tell me)(?: my| the)? )?battery"
         r"(?: level| status| percentage| life| left| charge)?"
         r"|how much battery(?: do i have| is left)?(?: left)?"
         r"|(?:is|am) (?:my |the )?(?:laptop|pc|computer|i) charging", "battery_status"),
        (r"(?:how much )?(?:ram|memory) (?:usage|use|is used|am i using|left|is left|is free|free)"
         r"|how much (?:ram|memory)(?: am i using| is used| is free| is left| do i have(?: left)?)?"
         r"|(?:check|show)(?: my)? (?:ram|memory)(?: usage)?"
         r"|(?:whats|what is)(?: my| the)? (?:ram|memory) usage", "memory_usage"),
        (r"(?:how much )?(?:free )?(?:disk|storage|drive) space(?: do i have| is left| left)?"
         r"|how much (?:disk|storage)(?: space)?(?: do i have| is left| left)?"
         r"|(?:check|show)(?: my)? (?:disk|storage)(?: space)?|free space"
         r"|(?:whats|what is)(?: my| the)? (?:free )?(?:disk|storage) space", "disk_space"),
        (r"(?:(?:whats|what is) )?(?:my |the )?uptime"
         r"|how long (?:has|have) (?:my |the |this )?(?:pc|computer|system|laptop) been (?:on|running|up)",
         "uptime"),
        (r"am i (?:online|connected)(?: to the internet)?|is (?:the )?internet (?:working|on|connected|up)"
         r"|do i have (?:internet|a connection|an internet connection)|are we online", "network_status"),
    )
)

# Ordered: the longer, more specific trigger first so "search google for x"
# isn't swallowed by "google ".
_SEARCH_TRIGGERS = (
    "search google for",
    "search the web for",
    "search for",
    "google",
)

_SEARCH_PATTERNS = tuple(
    re.compile(rf"^\s*{re.escape(trigger)}\s+(.+?)[\s?.!]*$", re.IGNORECASE)
    for trigger in _SEARCH_TRIGGERS
)


def _word_pattern(phrase):
    """A regex matching `phrase` only as whole words ("mute" not "commute")."""

    return re.compile(rf"(?<!\w){re.escape(normalize(phrase))}(?!\w)")


_OPEN_APP_PATTERNS = tuple(
    (_word_pattern(phrase), name) for phrase, name in _OPEN_APPS.items()
)

_CLOSE_APP_PATTERNS = tuple(
    (_word_pattern(phrase), name) for phrase, name in _CLOSE_APPS.items()
)

_OPEN_GOOGLE_PATTERN = _word_pattern("open google")

_SUBSTRING_PATTERNS = tuple(
    (tuple(_word_pattern(p) for p in phrases), call)
    for phrases, call in _SUBSTRING_TOOLS
)


def _first_named(query, patterns, tool_name):

    for pattern, name in patterns:

        if pattern.search(query):

            return ToolCall(tool_name, {"name": name})

    return None


def _match_open_app(query, raw_query):

    return _first_named(query, _OPEN_APP_PATTERNS, "open_app")


def _match_open_google(query, raw_query):

    # The zero-arg homepage tool; checked before the search triggers.
    if _OPEN_GOOGLE_PATTERN.search(query):

        return ToolCall("open_google", {})

    return None


def _match_close_app(query, raw_query):

    return _first_named(query, _CLOSE_APP_PATTERNS, "close_app")


def _strip_fillers(query):
    """Drop a leading 'hey jarvis' / 'please' and a trailing 'please'."""

    query = re.sub(r"^(?:(?:hey|ok|okay) )?jarvis ", "", query)

    query = re.sub(r"^please ", "", query)

    return re.sub(r" (?:please|jarvis)$", "", query).strip()


_REMEMBER = re.compile(r"(?:please )?(?:remember|dont forget|do not forget)(?: that)? (.+)")

_NOTE = re.compile(r"(?:please )?(?:note that|make a note(?: that)?|take a note(?: that)?) (.+)")

_RAW_REMEMBER = re.compile(
    r"^\W*(?:please\s+)?(?:remember|don'?t forget|do not forget|note that|make a note|take a note)"
    r"(?:\s+that)?\s+(.+?)[\s.!?]*$",
    re.IGNORECASE,
)

_RECALL = re.compile(r"what (?:else )?do you (?:remember|know)(?: about me)?|what have i told you(?: about me)?")

_PROFILE_QUESTION = re.compile(
    r"(?:whats|what is|do you know|do you remember|tell me) my "
    r"(name|city|birthday|job|goal|favou?rite [a-z]+(?: [a-z]+)?)"
)

_FORGET = re.compile(r"(?:please )?forget (?:that |about )?(?:my )?(?!it$)(.+)")


def _match_memory(query, raw_query):
    """Memory commands come first: "remember to open notepad" must be saved,
    not executed."""

    text = _strip_fillers(query)

    match = _REMEMBER.fullmatch(text) or _NOTE.fullmatch(text)

    if match:

        raw = _RAW_REMEMBER.match(raw_query or "")

        return ToolCall("remember_fact", {"text": raw.group(1) if raw else match.group(1)})

    if _RECALL.fullmatch(text):

        return ToolCall("recall_memory", {})

    match = _PROFILE_QUESTION.fullmatch(text)

    if match:

        return ToolCall("get_profile_value", {"key": match.group(1)})

    match = _FORGET.fullmatch(text)

    if match:

        return ToolCall("forget_memory", {"query": match.group(1)})

    return None


_FOLDER_NAMES = "desktop|documents|downloads|pictures|music|videos|workspace"

# "show my workspace" stays the spoken list_files; "open my workspace" opens it.
_OPEN_FOLDER = re.compile(
    rf"open(?: up)? (?:my |the )?({_FOLDER_NAMES})(?: folder)?"
    r"|show(?: me)? (?:my |the )?(desktop|documents|downloads|pictures|music|videos)(?: folder)?"
)

_OPEN_PICK = re.compile(
    r"open (?:the )?(first|second|third|fourth|fifth|last|1st|2nd|3rd)(?: one| file| result)?"
    r"|open (it|that|this)(?: file)?"
)

_OPEN_MY_FILE = re.compile(r"open (?:up )?my (.+)")

_OPEN_NAMED_FILE = re.compile(r"open (?:the )?(?:file )?(.+\.[a-z0-9]{1,5})")

# "find my X", "find (the) file X", "find X.ext", "where is my X" — not a bare
# "find X", which is usually a web-style request ("find a restaurant").
_FIND_FILE = re.compile(
    r"(?:find|locate) (?:my |the file |file )(?:called |named )?(.+?)(?: file)?"
    r"|(?:find|locate) (.+\.[a-z0-9]{1,5})"
    r"|where(?: is|s) my (.+?)(?: file)?"
)

_RECENT = re.compile(
    r"(?:(?:show|list|open|what are)(?: me)? )?(?:my )?recent(?:ly opened)? files"
    r"|what (?:files )?did i open recently"
)


def _first_group(match):

    return next(group for group in match.groups() if group)


def _match_files(query, raw_query):

    text = spoken_filename(_strip_fillers(query))

    match = _OPEN_FOLDER.fullmatch(text)

    if match:

        return ToolCall("open_folder", {"folder": _first_group(match)})

    match = _OPEN_PICK.fullmatch(text)

    if match and conversation.results():

        return ToolCall("open_file", {"name": _first_group(match)})

    match = _OPEN_MY_FILE.fullmatch(text) or _OPEN_NAMED_FILE.fullmatch(text)

    if match:

        return ToolCall("open_file", {"name": match.group(1)})

    match = _FIND_FILE.fullmatch(text)

    if match:

        return ToolCall("find_file", {"name": _first_group(match)})

    if _RECENT.fullmatch(text):

        return ToolCall("recent_files", {})

    return None


def _match_info(query, raw_query):

    text = _strip_fillers(query)

    for pattern, tool_name in _INFO_PATTERNS:

        if pattern.fullmatch(text):

            return ToolCall(tool_name, {})

    return None


_CITY = r"(?: in ([a-z][a-z .-]*?))?"

_WEATHER_PATTERNS = tuple(re.compile(pattern) for pattern in (
    rf"(?:(?:whats|what is|hows|how is) )?(?:the )?weather(?: like)?(?: today| now| right now)?{_CITY}"
    rf"(?: today| now| right now)?",
    rf"(?:whats|what is) the temperature(?: outside)?{_CITY}(?: today| now| right now)?",
    rf"(?:will it|is it going to|is it) (?:rain|snow)(?:ing)?(?: today)?{_CITY}(?: today)?",
    rf"(?:weather|temperature|forecast){_CITY}",
))


def _match_weather(query, raw_query):
    """Today's weather only — "tomorrow" is left to the LLM, which says it
    doesn't know rather than reading out today's forecast."""

    text = _strip_fillers(query)

    for pattern in _WEATHER_PATTERNS:

        match = pattern.fullmatch(text)

        if match:

            city = (match.group(1) or "").strip()

            return ToolCall("weather", {"city": city} if city else {})

    return None


# (normalized pattern, raw pattern keeping case, max topic words)
_LOOKUP_PATTERNS = tuple(
    (re.compile(norm), re.compile(raw, re.IGNORECASE), max_words) for norm, raw, max_words in (
        (r"who (?:is|was|are|were) (.+)", r"^\W*who\s+(?:is|was|are|were)\s+(.+?)[\s?.!]*$", 5),
        (r"(?:what is|what are|what was|whats) (?:an? |the )?(.+)",
         r"^\W*what(?:'s|s|\s+is|\s+are|\s+was)\s+(?:an?\s+|the\s+)?(.+?)[\s?.!]*$", 3),
        (r"tell me about (.+)", r"^\W*tell\s+me\s+about\s+(.+?)[\s?.!]*$", 5),
        (r"define (.+)", r"^\W*define\s+(.+?)[\s?.!]*$", 3),
        (r"what does (.+) mean", r"^\W*what\s+does\s+(.+?)\s+mean[\s?.!]*$", 3),
    )
)

# Follow-ups and chit-chat, not topics: the LLM (with conversation history) takes them.
_LOOKUP_STOP_WORDS = {
    "he", "she", "it", "that", "this", "they", "him", "her", "them", "you",
    "up", "new", "wrong", "happening", "going on", "your name",
}

_LOOKUP_STOP_FIRST = {"my", "your", "our", "this", "that", "it", "his", "her", "their"}


def _match_lookup(query, raw_query):

    text = _strip_fillers(query)

    for pattern, raw_pattern, max_words in _LOOKUP_PATTERNS:

        match = pattern.fullmatch(text)

        if not match:

            continue

        topic = match.group(1).strip()

        words = topic.split()

        if topic in _LOOKUP_STOP_WORDS or words[0] in _LOOKUP_STOP_FIRST or len(words) > max_words:

            return None

        raw = raw_pattern.match(raw_query or "")

        return ToolCall("lookup", {"topic": raw.group(1).strip() if raw else topic})

    return None


def _match_calc(query, raw_query):
    """Arithmetic, only when the whole utterance parses as maths (so "what is
    python" is never sent to the calculator). Uses the raw text: normalizing
    strips '*', '+', '^' and '1,000'."""

    expression = parse_math(raw_query) or parse_math(query)

    if expression is None:

        return None

    return ToolCall("calculate", {"expression": expression})


def _match_substring_tool(query, raw_query):
    """First zero-arg tool with a trigger phrase present as whole words."""

    for patterns, call in _SUBSTRING_PATTERNS:

        if any(p.search(query) for p in patterns):

            return call

    return None


def _search_term(trigger_pattern, query, raw_query):
    """The text after a search trigger, from the raw utterance when it matches
    there (keeps case: "search for Tony Stark" -> "Tony Stark")."""

    for text in (raw_query, query):

        match = trigger_pattern.match(text or "")

        if match and match.group(1).strip():

            return match.group(1).strip()

    return None


def _match_search(query, raw_query):

    for pattern in _SEARCH_PATTERNS:

        term = _search_term(pattern, query, raw_query)

        if term:

            return ToolCall("search_web", {"query": term})

    return None


# Checked in order; first match wins.
_MATCHERS = (
    _match_memory,
    _match_files,
    _match_open_app,
    _match_open_google,
    _match_close_app,
    _match_info,
    _match_calc,
    _match_substring_tool,
    _match_search,
    _match_weather,
    _match_lookup,
)


def resolve_keyword_tool(query, raw_query=None):
    """Map a known command phrase to a registry ToolCall, or None.

    Deterministic and LLM-free (importable in CI). The query is normalized here
    too, so voice and typed input match the same tables. `raw_query` (the
    un-normalized utterance) is used where an argument's case matters.
    """

    if raw_query is None:

        raw_query = query

    query = normalize(query)

    for matcher in _MATCHERS:

        call = matcher(query, raw_query)

        if call is not None:

            return call

    return None

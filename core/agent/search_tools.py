"""Local search across your files, indexed documents and remembered facts,
plus document search and re-indexing. Router-only; works offline."""

import re

from core.agent.fs_tools import (
    find_paths,
    folder_label,
    user_roots
)

from core.agent.registry import (
    Reply,
    tool
)

from core.memory.document_memory import (
    build_index,
    index_state,
    search_chunks
)

from core.memory.facts import (
    search_facts
)

from core.state.conversation import (
    conversation
)

from core.text import (
    plural
)


SNIPPET_WORDS = 25


@tool(
    "search_local",
    "Search your files, documents and memory",
    params={"query": {"type": "str", "required": True, "desc": "what to look for"}},
    llm=False,
)
def search_local(query):

    # "search for my notes" should find meeting_notes.docx: drop a leading my/the/a.
    query = re.sub(r"^(?:my|the|a|an)\s+", "", (query or "").strip(), flags=re.IGNORECASE)

    roots = user_roots()

    files = find_paths(query, roots)[:5]

    chunks = search_chunks(query, top_k=2) if index_state() == "ready" else []

    remembered = search_facts(query, k=2)

    conversation.set_results([str(path) for path in files])

    if not (files or chunks or remembered):

        return f"Nothing local for {query}. Say 'search the web for {query}' to look online."

    said, shown = [], []

    if files:

        said.append(f"{plural(len(files), 'file')}, like {files[0].name}")

        shown += ["Files:"] + [f"{p.name} ({folder_label(p, roots)})" for p in files]

    if chunks:

        said.append(f"a match in {chunks[0]['file']}")

        shown += ["Documents:"] + [f"{c['file']}: {c['text'][:200]}" for c in chunks]

    if remembered:

        said.append("something you asked me to remember")

        shown += ["Remembered:"] + remembered

    if len(said) > 1:

        said[-1] = "and " + said[-1]

    return Reply(say="I found " + ", ".join(said) + ".", show="\n".join(shown))


@tool(
    "search_my_documents",
    "Search inside your indexed PDF documents",
    params={"query": {"type": "str", "required": True, "desc": "what to look for"}},
    llm=False,
)
def search_my_documents(query):

    state = index_state()

    if state == "missing":

        return "Your documents aren't indexed yet. Say 'index my documents'."

    if state == "stale":

        return "Your documents changed since I indexed them. Say 'index my documents'."

    hits = search_chunks(query, top_k=2)

    if not hits:

        return f"Nothing in your documents about {query}."

    first = hits[0]

    words = first["text"].split()

    snippet = " ".join(words[:SNIPPET_WORDS]) + ("…" if len(words) > SNIPPET_WORDS else "")

    return Reply(
        say=f"In {first['file']}: {snippet}",
        show="\n\n".join(f"{hit['file']}:\n{hit['text']}" for hit in hits),
    )


@tool("index_documents", "Re-index the PDFs in your Jarvis documents folder", llm=False)
def index_documents():

    from core.memory.document_memory import DOCS_PATH

    files, _chunks = build_index()

    if not files:

        return Reply(
            say="I didn't find any PDFs to index.",
            show=f"Put PDFs in {DOCS_PATH}, then say 'index my documents'.",
        )

    return f"Indexed {plural(files, 'document')}."

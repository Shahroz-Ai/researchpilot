import ast
import operator

import trafilatura
from ddgs import DDGS

PAGE_CHUNK = 4000
_page_cache = {}

# ---------- Tool 1: web search ----------


def web_search(query, max_results=5):
    """Search the web and return titles, links, and short snippets."""
    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, start=1):
        lines.append(f"{i}. {r['title']}\n   URL: {r['href']}\n   {r['body']}")
    return "\n\n".join(lines)


# ---------- Tool 2: page reader (with pagination) ----------


def read_page(url, start=0):
    """Return one chunk of a page's text, starting at character offset `start`."""
    try:
        start = max(int(start), 0)
    except (TypeError, ValueError):
        start = 0

    try:
        text = _page_cache.get(url)
        if text is None:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return "Could not download this page."
            text = trafilatura.extract(downloaded)
            if not text:
                return "Could not extract readable text from this page."
            _page_cache[url] = text

        chunk = text[start : start + PAGE_CHUNK]
        if not chunk:
            return "No more text. You have already read the whole page."
        end = start + len(chunk)
        if end < len(text):
            chunk += (
                f"\n...[page continues. To read more, call read_page again "
                f"with start={end}]"
            )
        return chunk
    except Exception as e:
        return f"Failed to read page: {e}"


# ---------- Tool 3: calculator (safe, no eval) ----------

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression):
    """Evaluate a math expression like '(120 * 1.15) / 4'."""
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_eval_node(tree.body))
    except Exception as e:
        return f"Calculation error: {e}"


# ---------- Tool definitions for the model ----------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Returns titles, URLs, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": (
                "Read the text of a web page, about 4000 characters at a time. "
                "If the result says the page continues, call again with the given start value to read the next part."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full URL to read"},
                    "start": {
                        "type": "integer",
                        "description": "Character offset to start reading from. Default 0.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a math expression. Use it for any calculation instead of doing math yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "e.g. (120 * 1.15) / 4",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "web_search": web_search,
    "read_page": read_page,
    "calculator": calculator,
}


def run_tool(name, args):
    """Run a tool by name with the arguments the model gave."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Unknown tool: {name}"
    try:
        return func(**args)
    except TypeError as e:
        return f"Bad arguments for {name}: {e}"
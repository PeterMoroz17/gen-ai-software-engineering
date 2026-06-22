from pathlib import Path

from fastmcp import FastMCP

LOREM_PATH = Path(__file__).parent / "lorem-ipsum.md"
DEFAULT_WORD_COUNT = 30

mcp = FastMCP("lorem-ipsum-server")


def _read_words(word_count: int = DEFAULT_WORD_COUNT) -> str:
    text = LOREM_PATH.read_text(encoding="utf-8")
    words = text.split()
    return " ".join(words[:word_count])


@mcp.resource("lorem://text")
def lorem_text_default() -> str:
    """Lorem ipsum text, limited to the default word count."""
    return _read_words(DEFAULT_WORD_COUNT)


@mcp.resource("lorem://text/{word_count}")
def lorem_text(word_count: int) -> str:
    """Lorem ipsum text, limited to the given word count."""
    return _read_words(word_count)


@mcp.tool
def read(word_count: int = DEFAULT_WORD_COUNT) -> str:
    """Return the first `word_count` words from lorem-ipsum.md (default 30)."""
    return _read_words(word_count)


if __name__ == "__main__":
    mcp.run()

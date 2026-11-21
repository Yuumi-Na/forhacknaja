"""Read a DLD lab sheet photo with Claude on Bedrock (Strands structured output).

`strands` is imported lazily so importing this module needs no credentials or network.
The prompt only extracts what is printed. No arithmetic happens here.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any

from mordin.config import READER_MAX_TOKENS, make_bedrock_model
from mordin.data import Data
from mordin.vision.image import PreparedImage
from mordin.vision.schemas import SheetReading, validate_reading

PROMPT_FILE = Path(__file__).resolve().parents[3] / "prompts" / "read_lab_sheet_v1.md"
DEADLINE_SECONDS = 20
USER_TEXT = "Read this soil test sheet."


class ReadError(Exception):
    """The model call failed, timed out or returned no usable structured output."""


def load_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def _build_agent(system_prompt: str):
    """A fresh Agent per call, so no image or reading carries over between farmers."""
    from strands import Agent

    return Agent(
        model=make_bedrock_model(READER_MAX_TOKENS),
        system_prompt=system_prompt,
        callback_handler=None,
        tools=[],
    )


def _invoke(img: PreparedImage) -> Any:
    agent = _build_agent(load_prompt())
    content = [
        {"text": USER_TEXT},
        {"image": {"format": img.format, "source": {"bytes": img.data}}},
    ]
    return agent(content, structured_output_model=SheetReading)


def read_lab_sheet(img: PreparedImage, data: Data) -> SheetReading:
    """Return the validated reading. Raises ReadError on failure or after 20 seconds."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_invoke, img)
    try:
        result = future.result(timeout=DEADLINE_SECONDS)
    except FutureTimeout as exc:
        raise ReadError("model call exceeded the deadline") from exc
    except Exception as exc:  # model, network or config failure
        raise ReadError(f"model call failed: {type(exc).__name__}") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    reading = getattr(result, "structured_output", None)
    if not isinstance(reading, SheetReading):
        raise ReadError("model returned no structured output")
    return validate_reading(reading, data.limits)

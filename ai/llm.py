"""Gemini LLM client and the safe-invoke wrapper."""

import os
import threading
import time

from langchain_google_genai import ChatGoogleGenerativeAI

from config import GEMINI_MODEL


_llm = None
_llm_lock = threading.Lock()


def get_llm():
    """Return the shared Gemini client, creating it on first use.

    Created lazily (instead of at import time) so the missing-API-key check in
    app.py can show its friendly error before anything reads the key.
    """
    global _llm
    if _llm is None:
        with _llm_lock:
            if _llm is None:
                _llm = ChatGoogleGenerativeAI(
                    model=GEMINI_MODEL,
                    temperature=0.2,
                    google_api_key=os.environ["GEMINI_API_KEY"],
                    timeout=30,
                    max_retries=0,
                )
    return _llm


def safe_llm_invoke(structured_llm, prompt, max_attempts=2, base_delay=1.0):
    """
    Safely call the LLM without allowing the app to appear frozen.

    Each attempt has a client-side timeout configured on the Gemini client.
    Only transient errors are retried once.
    """
    last_err = None

    for attempt in range(max_attempts):
        try:
            return structured_llm.invoke(prompt)

        except Exception as e:
            last_err = e
            msg = str(e).lower()

            transient = any(
                k in msg
                for k in [
                    "rate",
                    "429",
                    "timeout",
                    "timed out",
                    "503",
                    "502",
                    "connection",
                    "temporarily unavailable",
                ]
            )

            if not transient or attempt == max_attempts - 1:
                raise

            time.sleep(base_delay)

    raise last_err

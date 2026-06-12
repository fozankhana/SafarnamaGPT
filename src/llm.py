import os
from typing import Generator

from config import cfg
from src.utils import setup_logger

logger = setup_logger(__name__)

# ── Agent system prompt ────────────────────────────────────────────────────────
AGENT_SYSTEM_PROMPT = """\
You are SafarnāmaGPT, a friendly and expert AI travel agent specializing in Pakistan tourism. \
Your job is to understand each traveler's unique plan and create personalized recommendations.

## YOUR BEHAVIOR
- Warmly greet the user and ask about their travel plans.
- Proactively ask clarifying questions to understand:
  1. How many days are they planning to travel?
  2. Which cities or regions do they want to visit (or ask for suggestions)?
  3. Their travel interests (adventure/trekking, history & heritage, culture & food, nature)?
  4. Travel style (budget backpacker, mid-range, luxury)?
- Once you have enough information (at minimum: days + city/region), generate a complete \
  day-by-day itinerary immediately without asking more questions.
- For EVERY specific place, monument, restaurant, or area you mention, append a clickable \
  Google Maps link in this EXACT format right after the name:
    [View on Map](https://www.google.com/maps/search/?api=1&query=PLACE+NAME+Pakistan)
  Replace spaces with + signs. Example:
    Lahore Fort [View on Map](https://www.google.com/maps/search/?api=1&query=Lahore+Fort+Pakistan)

## ITINERARY FORMAT
Structure each day clearly:
  **Day 1 – City Name**
  🌅 Morning: ...
  ☀️ Afternoon: ...
  🌆 Evening: ...
  🍽️ Food: ...
  🏨 Stay: ...

For each city include famous attractions, must-try local food, recommended area to stay, \
and practical travel tips (transport, weather, costs).

## IMPORTANT RULES
- Always use the knowledge context provided to give accurate facts.
- If the context lacks a specific detail, be honest but offer what you know.
- Keep the conversation natural and engaging — you are a passionate guide, not a Wikipedia article.
- After giving an itinerary, ask: "Would you like me to adjust the pace, add more details, \
  or include any specific interests?"
"""


class LLM:
    _instance = None

    @classmethod
    def get(cls) -> "LLM":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def __init__(self):
        if cfg.use_groq:
            self._init_groq()
        else:
            self._init_local()

    def _init_groq(self):
        import groq as groq_sdk
        api_key = cfg.groq_api_key or os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError(
                "Groq API key not set. Enter it in the sidebar or set the GROQ_API_KEY "
                "environment variable."
            )
        self.client = groq_sdk.Groq(api_key=api_key)
        self.mode = "groq"
        logger.info("Groq client ready (model: %s).", cfg.groq_model)

    def _init_local(self):
        model_path = cfg.model_path
        if not model_path.exists():
            raise FileNotFoundError(
                f"GGUF model not found at: {model_path}\n"
                "Set use_groq=True in config.py or download the model."
            )
        logger.info("Loading local LLM from: %s", model_path)
        from llama_cpp import Llama
        self.model = Llama(
            model_path=str(model_path),
            n_ctx=cfg.n_ctx,
            n_threads=cfg.n_threads,
            n_batch=cfg.n_batch,
            n_gpu_layers=cfg.n_gpu_layers,
            use_mlock=cfg.use_mlock,
            verbose=False,
        )
        self.mode = "local"
        logger.info("Local LLM loaded (n_ctx=%d).", cfg.n_ctx)

    def build_messages(self, query: str, context: str, history: list[dict] | None = None) -> list[dict]:
        """Build the messages list for chat completion APIs (Groq or OpenAI-compatible)."""
        history = history or []
        max_msgs = cfg.history_turns * 2
        trimmed = history[-max_msgs:] if len(history) > max_msgs else history

        system_content = AGENT_SYSTEM_PROMPT + "\n\n== Knowledge Base ==\n" + context
        messages = [{"role": "system", "content": system_content}]
        for msg in trimmed:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})
        return messages

    def build_prompt(self, query: str, context: str, history: list[dict] | None = None) -> str | list[dict]:
        """Returns messages list (Groq) or formatted string prompt (local)."""
        if self.mode == "groq":
            return self.build_messages(query, context, history)

        # Local Llama 3.2 manual prompt format
        history = history or []
        max_msgs = cfg.history_turns * 2
        trimmed = history[-max_msgs:] if len(history) > max_msgs else history

        system_ctx = (
            "<|start_header_id|>system<|end_header_id|>\n\n"
            + AGENT_SYSTEM_PROMPT
            + "\n\n== Knowledge Base ==\n"
            + context
            + "<|eot_id|>"
        )
        parts = [system_ctx]
        for msg in trimmed:
            role_tag = "user" if msg["role"] == "user" else "assistant"
            parts.append(
                f"<|start_header_id|>{role_tag}<|end_header_id|>\n\n"
                f"{msg['content']}<|eot_id|>"
            )
        parts.append(
            f"<|start_header_id|>user<|end_header_id|>\n\n{query}<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
        )
        return "".join(parts)

    def stream(self, prompt: str | list[dict]) -> Generator[str, None, None]:
        if self.mode == "groq":
            yield from self._stream_groq(prompt)
        else:
            yield from self._stream_local(prompt)

    def _stream_groq(self, messages: list[dict]) -> Generator[str, None, None]:
        response = self.client.chat.completions.create(
            model=cfg.groq_model,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            top_p=cfg.top_p,
            stream=True,
        )
        for chunk in response:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield token

    def _stream_local(self, prompt: str) -> Generator[str, None, None]:
        stop = ["<|eot_id|>", "<|end_of_text|>"]
        output = self.model(
            prompt,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            top_k=cfg.top_k,
            top_p=cfg.top_p,
            repeat_penalty=cfg.repeat_penalty,
            stream=True,
            echo=False,
            stop=stop,
        )
        for chunk in output:
            token = chunk["choices"][0]["text"]
            if token:
                yield token

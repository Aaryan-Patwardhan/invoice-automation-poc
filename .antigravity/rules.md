# Global Agent Directives

## 1. Operating Environment
- **OS:** Garuda Linux (Arch-based). Always use `pacman` or `paru` for system packages.
- **Shell:** Fish. Never use bash syntax. All exports use `set -x VAR value`, venv activation uses `source venv/bin/activate.fish`.
- **Hardware:** Intel i7-11800H, NVIDIA RTX 3050 Ti, 16GB RAM.

## 2. AI & Data Stack
- **Acceleration:** Always prioritize CUDA-enabled libraries (PyTorch, llama-cpp-python). Offload compute to the GPU, keep CPU free.
- **Environment:** Python via `venv` + `pip` only. No conda, no poetry.
- **Inference:** Favor local LLM inference via Ollama or llama-cpp-python for privacy and zero cost.

## 3. Project Context
- **Primary goal:** Freelance delivery projects (automation, Flask APIs, AI pipelines). Code must be client-ready — clean, documented, deployable.
- **Stack priorities:** Python, Flask, FastAPI, OpenCV, YOLO, local LLMs, Shell scripting.
- **Delivery model:** Product-first. Every feature must be demonstrable and shippable, not just functional locally.

## 4. Coding Philosophy
- **Logic First:** Explain the "why" and "how" in plain English before writing any code.
- **No Boilerplate:** Write concise, modular code. When refactoring, output only the changed functions/lines.
- **Fail Fast:** If requirements are ambiguous, stop and ask. Do not guess or hallucinate solutions.
- **Client Quality:** Code must include basic error handling, logging, and comments by default. No silent failures.


{
  "antigravity.agent.routing": {
    "inline_autocomplete": "Gemini 3 Flash",
    "chat_standard": "Gemini 3.1 Pro (Low)",
    "agentic_tasks": "Claude Sonnet 4.6 (Thinking)",
    "complex_refactoring": "Claude Opus 4.6 (Thinking)"
  }
}


## 8. Invoice POC — Current State
- extractor.py: TEXT path (qwen2.5:1.5b) + OCR path (qwen2.5vl:3b) both implemented
- app.py: Gradio UI with multi-file + direct image upload — DO NOT add Flask
- Next feature: Demo GIF / screenshot for README
- Do not change DB schema, do not change save_to_db()

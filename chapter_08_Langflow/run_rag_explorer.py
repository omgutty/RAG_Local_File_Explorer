"""Launch the RAG Explorer UI connected to Langflow."""

import os
import subprocess
import sys

REQUIRED = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "dotenv": "python-dotenv",
    "httpx": "httpx",
    "pydantic": "pydantic",
}


def _ensure_deps():
    missing = []
    for mod, pkg in REQUIRED.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"⚙️  Installing missing packages: {', '.join(missing)}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing]
        )


if __name__ == "__main__":
    # Jump to the script's own directory so all paths are relative
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    _ensure_deps()

    from dotenv import load_dotenv

    env_path = os.path.join("src", "rag_explorer", ".env")
    load_dotenv(env_path)

    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    print(f"[ RAG Explorer ]  http://127.0.0.1:{port}")

    # reload=False avoids watchfiles issues on Windows
    uvicorn.run(
        "src.rag_explorer.main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info",
    )

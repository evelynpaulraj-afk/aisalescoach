"""
launcher.py
Entry point for the desktop app. Double-clicking SalesCoach.exe runs this:
  1. picks a writable folder for settings, uploads and cached results
  2. points the speech libraries at the models bundled inside the app
  3. asks for a Gemini API key the first time (saved to a .env file)
  4. starts the local server and opens the UI in the default browser

It also works unpackaged:  python launcher.py
"""

import multiprocessing
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser

ENV_TEMPLATE = """# Sales Coach settings
# Get a free Gemini API key at https://aistudio.google.com/apikey
GEMINI_API_KEY=

# Optional: Whisper model size (tiny, base, small, medium). Bigger = more
# accurate but slower and needs more memory.
# WHISPER_MODEL=small
"""


def resource_dir() -> str:
    """Folder holding files bundled inside the app (the UI, the models)."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def app_dir() -> str:
    """Folder containing the .exe (or this script when run unpackaged)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def pick_user_dir() -> str:
    """
    Where settings, uploads and cached results live: next to the app if that
    folder is writable, otherwise in %LOCALAPPDATA%\\SalesCoach.
    """
    base = app_dir()
    try:
        probe = os.path.join(base, ".write_test")
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        return base
    except OSError:
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        fallback = os.path.join(root, "SalesCoach")
        os.makedirs(fallback, exist_ok=True)
        return fallback


def configure_bundled_models() -> None:
    """
    If speech models were bundled into the app, use them and stay offline for
    model downloads, so no Hugging Face account or token is needed. This must
    run before torch / huggingface_hub / pyannote are imported.
    """
    models_dir = os.path.join(resource_dir(), "models")
    hf_home = os.path.join(models_dir, "hf")
    if not os.path.isdir(hf_home):
        return
    os.environ["HF_HOME"] = hf_home
    os.environ["HF_HUB_OFFLINE"] = "1"
    marker = os.path.join(models_dir, "whisper_model.txt")
    if os.path.exists(marker):
        with open(marker) as f:
            os.environ.setdefault("WHISPER_MODEL", f.read().strip())


def save_key(env_path: str, key: str) -> None:
    lines = []
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = f.read().splitlines()
    out, done = [], False
    for line in lines:
        if line.startswith("GEMINI_API_KEY="):
            out.append(f"GEMINI_API_KEY={key}")
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f"GEMINI_API_KEY={key}")
    with open(env_path, "w") as f:
        f.write("\n".join(out) + "\n")


def load_settings(user_dir: str) -> None:
    """Loads .env, creating it and asking for the Gemini key on first run."""
    from dotenv import load_dotenv

    env_path = os.path.join(user_dir, ".env")
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(ENV_TEMPLATE)
    load_dotenv(env_path)

    if not os.environ.get("GEMINI_API_KEY", "").strip():
        print("\nFirst-time setup: the analysis step needs a Gemini API key.")
        print("Get a free one at https://aistudio.google.com/apikey\n")
        key = input("Paste your Gemini API key and press Enter: ").strip().strip("\"'")
        if not key:
            input("No key entered. Run the app again when you have one. Press Enter to close...")
            sys.exit(1)
        save_key(env_path, key)
        os.environ["GEMINI_API_KEY"] = key
        print(f"Saved to {env_path}\n")


def find_free_port(start: int = 8000, tries: int = 20) -> int:
    for port in range(start, start + tries):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found between 8000 and 8019.")


def open_when_ready(url: str) -> None:
    """Opens the browser once the server answers, instead of guessing a delay."""
    for _ in range(600):  # model libraries can take a while to import
        try:
            with urllib.request.urlopen(url + "/health", timeout=1) as resp:
                if resp.status == 200:
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(1)


def main() -> None:
    user_dir = pick_user_dir()
    os.chdir(user_dir)  # the pipeline's relative "data/..." folders land here
    configure_bundled_models()
    load_settings(user_dir)

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    print("Starting Sales Coach. The first start can take a minute...")
    threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()

    import uvicorn
    from server import app  # imported late so the settings above apply first

    print(f"\nSales Coach is running at {url}")
    print(f"Your recordings and reports are stored in: {os.path.join(user_dir, 'data')}")
    print("Close this window to stop the app.\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    multiprocessing.freeze_support()  # required for frozen Windows apps
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        input("\nSomething went wrong (details above). Press Enter to close...")
        sys.exit(1)

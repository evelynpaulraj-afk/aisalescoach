
"""
prefetch_models.py
Run once at build time (build_app.ps1 does this for you). Downloads the speech
models into ./models/hf so PyInstaller can bundle them. The finished app then
needs no Hugging Face account, token or internet access for these models.
 
Needs HF_TOKEN in your environment or .env, and you must have accepted the
terms on the pyannote model pages (the same setup you already use to run the
pipeline locally).
 
    python prefetch_models.py
"""
 
import glob
import os
import shutil
import sys
 
from dotenv import load_dotenv
 
# override=True: the .env file wins over a stale HF_TOKEN left in the terminal
# session or Windows environment (a refreshed token otherwise gets ignored).
load_dotenv(override=True)
 
MODELS_DIR = os.path.abspath("models")
HF_HOME = os.path.join(MODELS_DIR, "hf")
os.makedirs(HF_HOME, exist_ok=True)
 
# Must be set BEFORE huggingface_hub is imported, or it caches elsewhere.
os.environ["HF_HOME"] = HF_HOME
os.environ.pop("HF_HUB_OFFLINE", None)
 
 
def materialize_cache(hub_dir: str) -> None:
    """
    The Hugging Face cache stores each file once in blobs/ and links to it from
    snapshots/. PyInstaller follows links and would copy every file twice.
    Replace the links with real files and drop blobs/ so each file ships once.
    Loading from snapshots/ (what offline mode does) is unaffected.
    """
    for root, _dirs, files in os.walk(hub_dir):
        for name in files:
            path = os.path.join(root, name)
            if os.path.islink(path):
                target = os.path.realpath(path)
                os.remove(path)
                shutil.copy2(target, path)
    for blobs in glob.glob(os.path.join(hub_dir, "models--*", "blobs")):
        shutil.rmtree(blobs)
 
 
REQUIRED_GATED_REPOS = (
    "pyannote/speaker-diarization-3.1",
    "pyannote/segmentation-3.0",
)
 
 
def get_token() -> str:
    """Reads HF_TOKEN, tolerating stray spaces or quotes copied into .env."""
    token = (os.environ.get("HF_TOKEN") or "").strip().strip("\"'").strip()
    if not token:
        sys.exit(
            "HF_TOKEN is empty or not set. Add a line like HF_TOKEN=hf_xxxxxxxx to the "
            ".env file in this folder (no spaces around =, no quotes)."
        )
    if token.lower().startswith("your") or "token" in token.lower() and not token.startswith("hf_"):
        sys.exit("HF_TOKEN looks like a placeholder, not a real token. Paste your real token into .env.")
    return token
 
 
def check_hf_access(token: str) -> None:
    """
    Fails fast, with a specific reason, before any big download starts.
    Separates the three usual causes: bad token, no licence accepted, or a
    fine-grained token missing the permission for gated repos.
    """
    from huggingface_hub import HfApi
 
    api = HfApi()
    try:
        account = api.whoami(token=token)["name"]
    except Exception:
        sys.exit(
            "Hugging Face rejected HF_TOKEN (invalid, expired or revoked).\n"
            "Create a new token at https://huggingface.co/settings/tokens and put it in .env.\n"
            "A classic token with 'Read' access is simplest."
        )
    print(f"[prefetch] Hugging Face token accepted (account: {account})")
 
    for repo in REQUIRED_GATED_REPOS:
        try:
            api.auth_check(repo, token=token)
        except Exception as exc:
            sys.exit(
                f"This account ({account}) cannot access {repo} ({type(exc).__name__}).\n"
                f"1. Open https://huggingface.co/{repo} while signed in as {account} and accept the conditions.\n"
                "2. If your token is 'fine-grained', enable 'Read access to contents of all public gated "
                "repos you can access' on it, or just use a classic Read token.\n"
                "Then run the build again."
            )
        print(f"[prefetch] Access to {repo}: OK")
 
 
def main() -> None:
    size = os.environ.get("WHISPER_MODEL", "small")
    token = get_token()
    os.environ["HF_TOKEN"] = token  # so every download below is authenticated
    print(f"[prefetch] Using HF_TOKEN {token[:7]}... (length {len(token)}; "
          "a real token is usually 37 characters)")
    check_hf_access(token)
 
    print(f"[prefetch] Downloading Whisper '{size}' ...")
    from faster_whisper import WhisperModel
 
    WhisperModel(size, device="cpu", compute_type="int8")
 
    print("[prefetch] Downloading pyannote speaker-diarization-3.1 (and its sub-models) ...")
    from pyannote.audio import Pipeline
 
    Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=token)
 
    materialize_cache(os.path.join(HF_HOME, "hub"))
    with open(os.path.join(MODELS_DIR, "whisper_model.txt"), "w") as f:
        f.write(size)
 
    total = sum(
        os.path.getsize(os.path.join(r, n)) for r, _d, fs in os.walk(MODELS_DIR) for n in fs
    )
    print(f"[prefetch] Done. {total / 1e9:.2f} GB in {MODELS_DIR}")
 
 
if __name__ == "__main__":
    main()
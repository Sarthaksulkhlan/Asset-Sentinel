"""Run Render pre-Gunicorn initialization with complete failure diagnostics."""

import sys
import traceback


def main() -> int:
    try:
        print("[STARTUP] Import: loading Flask application", flush=True)
        from backend.main import initialize_backend_runtime

        print("[STARTUP] Import: complete", flush=True)
        if not initialize_backend_runtime(start_agent=False, exit_on_error=False):
            return 1
        return 0
    except BaseException as exc:
        print("[STARTUP] FATAL: backend import or initialization failed", file=sys.stderr, flush=True)
        print(f"[STARTUP] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

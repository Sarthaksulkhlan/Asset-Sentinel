from backend._bootstrap import bootstrap_paths

bootstrap_paths()

from backend.main import app, initialize_backend_runtime, print_backend_banner, run_backend


if __name__ == "__main__":
    run_backend()


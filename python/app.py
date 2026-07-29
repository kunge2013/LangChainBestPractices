"""
LangGraph dev server entrypoint for debugging.

Usage:
    python app.py                     # Default: host=127.0.0.1 port=2024
    python app.py --port 8000         # Custom port
    python app.py --host 0.0.0.0      # Custom host
    python app.py --no-reload         # Disable auto-reload for debugging
    python app.py --debug-port 5678   # Enable debugpy for VSCode attach
"""
# Must be set BEFORE any other imports to avoid GBK encoding errors on Windows
import os
import sys

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def main():
    import argparse
    import asyncio
    import json
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()

    CONFIG_FILE = Path(__file__).parent / "langgraph.json"

    parser = argparse.ArgumentParser(description="LangGraph dev server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=2024,
        help="Port to bind (default: 2024)",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload for debugging",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Skip opening browser",
    )
    parser.add_argument(
        "--debug-port",
        type=int,
        help="Enable debugpy on this port for VSCode attach debugging",
    )
    parser.add_argument(
        "--wait-for-client",
        action="store_true",
        help="Wait for debugger client before starting server",
    )
    args = parser.parse_args()

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    graphs = config.get("graphs", {})
    env = config.get("env")

    # Resolve env file
    if isinstance(env, str):
        env_path = Path(__file__).parent / env
        if env_path.exists():
            load_dotenv(env_path, override=True)

    # Add project directories to sys.path
    # Use Path.cwd() instead of os.getcwd() to avoid blocking in async context
    cwd = Path.cwd()
    sys.path.append(str(cwd))
    for dep in config.get("dependencies", []):
        dep_path = cwd / dep
        if dep_path.is_dir() and dep_path.exists():
            sys.path.append(str(dep_path))

    # Optional: debugpy for VSCode remote debugging
    if args.debug_port:
        import debugpy

        debugpy.listen(("0.0.0.0", args.debug_port))
        print(f"debugpy listening on port {args.debug_port}")
        if args.wait_for_client:
            print("Waiting for debugger to attach...")
            debugpy.wait_for_client()
            print("Debugger attached!")

    from langgraph_api.cli import run_server

    print(f"\nStarting LangGraph dev server...")
    print(f"  Graphs: {list(graphs.keys())}")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Reload: {not args.no_reload}")
    print(f"  API Docs: http://{args.host}:{args.port}/docs")
    print(f"  Studio UI: https://smith.langchain.com/studio/?baseUrl=http://{args.host}:{args.port}")
    if args.debug_port:
        print(f"  Debugpy: port {args.debug_port} (attach VSCode debugger here)")
    print()

    run_server(
        args.host,
        args.port,
        reload=not args.no_reload,
        graphs=graphs,
        n_jobs_per_worker=None,
        open_browser=not args.no_browser,
        debug_port=None,
        env=env,
        store=None,
        wait_for_client=False,
        auth=None,
        http=None,
        ui=None,
        ui_config=None,
        webhooks=None,
        studio_url=None,
        allow_blocking=False,
        tunnel=False,
        server_level="DEBUG",
        checkpointer=None,
        disable_persistence=False,
        ssl_certfile=None,
        ssl_keyfile=None,
    )


if __name__ == "__main__":
    main()

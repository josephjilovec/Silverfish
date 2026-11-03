"""python -m silvertrap --help"""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import secrets
import sys

from .config import Config
from .reports import bundle, markdown, verify_bundle
from .server import Server
from .service import Service


def main():
    parser = argparse.ArgumentParser(description="SilverTrap fraud research command center")
    parser.add_argument("--data-dir", type=Path, help="Local database directory (default ./data)")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Start the authenticated local dashboard")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--seed", action="store_true", help="Seed three clearly marked simulations when database is empty")
    sub.add_parser("seed", help="Create sample simulations in an empty database")
    simulate = sub.add_parser("simulate", help="Run a synthetic scenario and print its report")
    simulate.add_argument("scenario", choices=["tech-support", "social-security", "medicare", "romance", "investment", "government", "grandparent", "benign", "injection"])
    export = sub.add_parser("export", help="Export a case to a JSON evidence bundle")
    export.add_argument("case_id")
    export.add_argument("output", type=Path)
    verify = sub.add_parser("verify", help="Verify an exported evidence bundle")
    verify.add_argument("input", type=Path)
    backup = sub.add_parser("backup", help="Consistent SQLite backup, including committed WAL data")
    backup.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        try:
            valid = verify_bundle(json.loads(args.input.read_text()))
        except (ValueError, OSError):
            valid = False
        print("Evidence checks passed" if valid else "Evidence verification FAILED")
        return 0 if valid else 1
    config = Config.from_env()
    if args.data_dir:
        config = replace(config, data_dir=args.data_dir.resolve())
    config.data_dir.mkdir(parents=True, exist_ok=True)
    try:
        config.data_dir.chmod(0o700)
    except OSError:
        pass
    if args.command == "serve":
        code_path = config.data_dir / "operator_token"
        code = config.operator_token
        if not code:
            if code_path.exists():
                code = code_path.read_text().strip()
            else:
                code = secrets.token_urlsafe(36)
                fd = os.open(code_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as output:
                    output.write(code)
        config = replace(config, operator_token=code, host=args.host or config.host, port=args.port if args.port is not None else config.port)
    service = Service(config)
    try:
        if args.command == "serve":
            if args.seed:
                service.seed()
            server = Server((config.host, config.port), service)
            print(f"SilverTrap · http://{config.host}:{server.server_port}", flush=True)
            print(f"Operator access code: {config.operator_token}", flush=True)
            print("Simulation & controlled research. External message delivery is not installed.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        elif args.command == "seed":
            service.seed()
            print("Sample cases ready")
        elif args.command == "simulate":
            case = service.create_case(scenario=args.scenario)
            print(markdown(service.simulate(case["id"], all_steps=True)))
        elif args.command == "export":
            args.output.write_text(json.dumps(bundle(service.get_case(args.case_id)), indent=2, ensure_ascii=False)+"\n")
            print(f"Exported {args.output}")
        elif args.command == "backup":
            print(f"Backup saved: {service.store.backup(args.output)}")
    finally:
        service.store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

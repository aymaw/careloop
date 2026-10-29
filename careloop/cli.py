import argparse
import json
from pathlib import Path

from .service import CareLoop


def seed(service):
    for p in [
        ("demo-harbor", "rehab", "north", 2),
        ("demo-orbit", "imaging", "north", 1),
        ("demo-meadow", "rehab", "south", 0),
    ]:
        service.add_provider(*p)
    for i, kind, region in [
        ("DEMO-001", "rehab", "north"),
        ("DEMO-002", "imaging", "north"),
        ("DEMO-003", "rehab", "south"),
    ]:
        service.create(i, kind, region, "demo-coordinator", "2030-01-01T09:00:00Z")


def demo():
    service = CareLoop()
    try:
        seed(service)
        proposal = service.propose("DEMO-001")
        service.approve(proposal, "demo-reviewer", "2030-01-01T10:00:00Z", "route-001")
        for version, action, data, at in [
            (1, "accept", {}, "2030-01-01T11:00:00Z"),
            (2, "schedule", {"slot": "2030-01-03T09:00:00Z"}, "2030-01-01T12:00:00Z"),
            (3, "complete", {"receipt": "DEMO-RECEIPT-001"}, "2030-01-03T10:00:00Z"),
            (4, "close", {"receipt": "DEMO-RECEIPT-001"}, "2030-01-03T11:00:00Z"),
        ]:
            service.command(
                "DEMO-001", action, data, version, "demo-coordinator", at, "demo-" + action
            )
        return {
            "project": "CareLoop",
            "mode": "synthetic-operations",
            "proposal": proposal,
            "no_capacity": service.propose("DEMO-003"),
            "audit_verified": service.verify_audit("DEMO-001"),
            "worklist": service.worklist("2030-01-04T12:00:00Z"),
            **service.export(),
        }
    finally:
        service.close()


def run_cli():
    parser = argparse.ArgumentParser(description="Synthetic closed-loop referral operations")
    parser.add_argument("--db", default=".runs/careloop.sqlite")
    sub = parser.add_subparsers(dest="command", required=True)
    demo_command = sub.add_parser("demo")
    demo_command.add_argument("--html", type=Path)
    sub.add_parser("seed")
    sub.add_parser("export")
    work = sub.add_parser("worklist")
    work.add_argument("now")
    propose = sub.add_parser("propose")
    propose.add_argument("referral")
    propose.add_argument("--model", action="store_true")
    approve = sub.add_parser("approve")
    approve.add_argument("proposal", type=Path)
    for field in ("actor", "at", "key"):
        approve.add_argument(field)
    command = sub.add_parser("command")
    for field in ("referral", "action", "data", "actor", "at", "key"):
        command.add_argument(field)
    command.add_argument("--version", type=int, required=True)
    args = parser.parse_args()
    if args.command == "demo":
        result = demo()
        if args.html:
            from .report import render

            render(result, args.html)
        print(json.dumps(result, indent=2))
        return
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    service = CareLoop(args.db)
    try:
        if args.command == "seed":
            seed(service)
            result = service.export()
        elif args.command == "propose":
            from .provider import ChatPlanner

            result = service.propose(args.referral, ChatPlanner.from_env() if args.model else None)
        elif args.command == "approve":
            result = service.approve(
                json.loads(args.proposal.read_text()), args.actor, args.at, args.key
            )
        elif args.command == "command":
            result = service.command(
                args.referral,
                args.action,
                json.loads(args.data),
                args.version,
                args.actor,
                args.at,
                args.key,
            )
        elif args.command == "worklist":
            result = service.worklist(args.now)
        else:
            result = service.export()
        print(json.dumps(result, indent=2))
    finally:
        service.close()


def main():
    import sqlite3
    import sys

    try:
        run_cli()
    except (ValueError, KeyError, OSError, sqlite3.Error, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from None

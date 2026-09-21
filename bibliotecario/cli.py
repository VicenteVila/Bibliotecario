"""CLI interactivo Bibliotecario: pregunta sobre papers o pide implementaciones."""
from __future__ import annotations

import argparse
import sys

import bibliotecario.api as API


def cmd_status(_a):
    import json
    print(json.dumps(API.status(), indent=1, ensure_ascii=False))


def cmd_ingest(a):
    r = API.ingest(a.source, ocr=a.ocr)
    print(("OK" if r.ok else "FALLO"), r.title, f"chunks={r.chunks} q={r.quality_score:.0f}", r.error)


def cmd_ask(a):
    r = API.ask(a.question, max_turns=a.turns)
    print(f"\n{r['answer']}\n")
    print(f"(turnos: {r['turns']}, evidencias: {len(r['evidence'])}, run: {r['run_id']})")


def cmd_blueprint(a):
    import json
    print(json.dumps(API.blueprint(a.technique, a.goal), indent=1, ensure_ascii=False)[:4000])


def cmd_implement(a):
    import json
    print(json.dumps(API.implement(a.technique, a.goal), indent=1, ensure_ascii=False))


def cmd_evolve(_a):
    import json
    print(json.dumps(API.evolve(), indent=1, ensure_ascii=False, default=str))


def cmd_repl(_a):
    print("Bibliotecario — pregunta sobre papers ('implementa X para Y' genera blueprint; 'salir' termina).")
    API.init()
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in ("salir", "exit", "quit"):
            break
        if q.lower().startswith("implementa "):
            rest = q[len("implementa "):]
            tech, _, goal = rest.partition(" para ")
            print(API.implement(tech.strip(), (goal or "agente nuevo").strip()))
            continue
        if q.lower().startswith("blueprint "):
            rest = q[len("blueprint "):]
            tech, _, goal = rest.partition(" para ")
            bp = API.blueprint(tech.strip(), (goal or "agente nuevo").strip())
            print(f"\n{ bp['blueprint']}\n")
            continue
        r = API.ask(q)
        print(f"\n{r['answer']}\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bibliotecario", description="Agente de búsqueda sobre papers")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.set_defaults(f=cmd_status)
    s = sub.add_parser("ingest"); s.add_argument("source"); s.add_argument("--ocr", action="store_true"); s.set_defaults(f=cmd_ingest)
    s = sub.add_parser("ask"); s.add_argument("question"); s.add_argument("--turns", type=int, default=10); s.set_defaults(f=cmd_ask)
    s = sub.add_parser("blueprint"); s.add_argument("technique"); s.add_argument("goal"); s.set_defaults(f=cmd_blueprint)
    s = sub.add_parser("implement"); s.add_argument("technique"); s.add_argument("goal"); s.set_defaults(f=cmd_implement)
    s = sub.add_parser("evolve"); s.set_defaults(f=cmd_evolve)
    s = sub.add_parser("repl"); s.set_defaults(f=cmd_repl)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    API.init()
    args.f(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

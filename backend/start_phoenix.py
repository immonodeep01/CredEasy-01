"""Start Phoenix locally for observability. Run: python start_phoenix.py"""
import os
os.environ.setdefault("PHOENIX_PORT", "6006")

from argparse import ArgumentParser, Namespace
from phoenix.server.cli.commands.serve import register

parser = ArgumentParser(prog="phoenix")
subparsers = parser.add_subparsers(dest="command")
register(subparsers)
args = parser.parse_args(["serve"])
# The subparsers inside `register` don't set `dest="command"`. Set it manually
# since phoenix's run() function reads `args.command` directly.
args.command = "serve"

print("Starting Phoenix on http://localhost:6006 ...")
from phoenix.server.cli.commands.serve import run
run(args)

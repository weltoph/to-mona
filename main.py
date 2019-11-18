#!python3
from parser import parse_file

import argparse
import logging


def write_tmp_file(content: str) -> str:
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(mode="w", delete=False) as tmp_file:
        print(content, file=tmp_file, flush=True)
        return tmp_file.name


def call_mona(scriptfile: str) -> str:
    from subprocess import run
    result = run(f"mona -q {scriptfile}",
                 capture_output=True, shell=True, encoding="utf-8")
    if result.returncode != 0:
        msg = f"error executing {result.args}:\n{result.stdout}"
        raise ChildProcessError(msg)
    return result.stdout


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("file",
                        help="file to be processed",
                        nargs="+")

    parser.add_argument("-d",
                        help=("increases debug output level"
                              + " " + "(can be specified more than once)"),
                        action="count",
                        default=0)

    parser.add_argument("-v",
                        help=("decreases debug output level"
                              + " " + "(can be specified more than once)"),
                        action="count",
                        default=0)

    args = parser.parse_args()

    verbosity = 3 + args.v - args.d
    verbosity = min(0, max(verbosity, 4))

    if args.d == 0:
        logging.basicConfig(level=logging.CRITICAL)
    elif args.d == 1:
        logging.basicConfig(level=logging.ERROR)
    elif args.d == 2:
        logging.basicConfig(level=logging.WARNING)
    elif args.d == 3:
        logging.basicConfig(level=logging.INFO)
    elif args.d == 4:
        logging.basicConfig(level=logging.DEBUG)

    for filename in args.file:
        parse_file(filename).normalize()


if __name__ == "__main__":
    main()

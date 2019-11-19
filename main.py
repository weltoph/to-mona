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

    parser.add_argument("-v",
                        help=("increases debug output level"
                              + " " + "(can be specified more than once)"),
                        action="count",
                        default=0)

    parser.add_argument("-q",
                        help=("decreases debug output level"
                              + " " + "(can be specified more than once)"),
                        action="count",
                        default=0)

    args = parser.parse_args()

    verbosity = 2 + args.v - args.q
    verbosity = max(0, min(verbosity, 4))

    if verbosity == 0:
        logging.basicConfig(level=logging.CRITICAL)
    elif verbosity == 1:
        logging.basicConfig(level=logging.ERROR)
    elif verbosity == 2:
        logging.basicConfig(level=logging.WARNING)
    elif verbosity == 3:
        logging.basicConfig(level=logging.INFO)
    elif verbosity == 4:
        logging.basicConfig(level=logging.DEBUG)

    for filename in args.file:
        parse_file(filename).normalize()


if __name__ == "__main__":
    main()

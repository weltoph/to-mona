#!python3
from parser import parse_file

import argparse
import logging

logger = logging.getLogger(__name__)


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
        n_interaction = parse_file(filename).normalize()
        logger.info("rendering base theory")
        base_theory = n_interaction.render_base_theory()
        for property_name in n_interaction.property_names:
            logger.info(f"checking {property_name}")
            proof_script = n_interaction.render_property_unreachability(
                    property_name,
                    base_theory)
            proof_file = write_tmp_file(proof_script)
            logger.info(f"writing proof script to {proof_file}")
            try:
                logger.info("calling mona")
                result = call_mona(proof_file)
            except ChildProcessError as e:
                logger.warning(f"mona reported error {e}")
                continue
            if "Formula is unsatisfiable" in result:
                if verbosity > 0:
                    print(f"{filename}: Successfully proven unreachability of "
                          + str(property_name))
            else:
                print(f"{filename}: Unable to prove unreachability of "
                      + str(property_name))


if __name__ == "__main__":
    main()

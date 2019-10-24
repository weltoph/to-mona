#!python3
from parser import parse
from mona import Analysis, list_all_models

import argparse
import sys
import lark

listable_elements = {
        "traps": "trap",
        "invariants": "invariant"
}


parser = argparse.ArgumentParser()

parser.add_argument("-l", "--list",
        help="lists structural invariants (requires --size)",
        action="store",
        choices=sorted(list(listable_elements)))

parser.add_argument("--size",
        help="specifies the size of the model to list structural invariants",
        action="store",
        metavar="N",
        type=int)

parser.add_argument("-s", "--statistics",
        help="changes output to statistics",
        action="store_true",
        default=False)

parser.add_argument("-v", "--verbose",
        help="makes statistics more verbose",
        action="store_true",
        default=False)

parser.add_argument("-p", "--check-property",
        help="checks only these property",
        action="append",
        type=str)

parser.add_argument("file",
        help="file to be proecessed",
        nargs="+")

args = parser.parse_args()

def list_elements():
    files = args.file
    for f in files:
        formula = parse(f)
        models = list_all_models(formula, listable_elements[args.list], args.size)
        print(f"{f}:\n")
        for model in models:
            print(model)

def perform_analyses():
    files = args.file
    first = True
    for f in files:
        try:
            formula = parse(f)
        except IsADirectoryError:
            print(f"skipping directory {f}", file = sys.stderr)
            continue
        except lark.exceptions.UnexpectedInput as e:
            print(f"cannot parse {f}, error in line {e.line}; skipping it",
                    file = sys.stderr)
            continue
        except lark.exceptions.LarkError:
            print(f"cannot parse {f}; skipping it", file = sys.stderr)
            continue
        analysis = Analysis(f, formula)
        properties = (args.check_property if args.check_property else
            formula.properties)
        for p in properties:
            analysis.perform_test(p)
        if args.statistics:
            analysis.print_statistics(without_header=not first,
                    small=not args.verbose)
        else:
            for r in analysis.results:
                msg = "disproven" if r.success else "potentially possible"
                print(f"{analysis.filename_short}: reachability of {r.property_name}: {msg}")
                if not r.success:
                    print(f"Potential counter-example:\n{r.model}")

        first = False

if args.list:
    if not args.size:
        parser.error("listing elements requires --size")
    else:
        list_elements()
else:
    perform_analyses()

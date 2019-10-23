from parser import parse
from mona import Analysis, list_all_models

import argparse
import sys
import lark

provable_properties = {
        "mutex": ("mutual exclusion", "nomutex"),
        "progress": ("progress", "deadlock")
}

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

parser.add_argument("-o", "--only-check",
        help="specifically checks only this property",
        action="store",
        choices=sorted(list(provable_properties.keys())),
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
        except lark.exceptions.ParseError:
            print(f"cannot parse {f}; skipping it", file = sys.stderr)
            continue
        analysis = Analysis(f, formula)
        if args.only_check:
            analysis.perform_test(*provable_properties[args.only_check])
        else:
            analysis.perform_test("progress", "deadlock")
            if formula.bound_to.has_critical_sections:
                analysis.perform_test("mutual exclusion", "nomutex")
        if args.statistics:
            analysis.print_statistics(without_header=not first,
                    small=not args.verbose)
        else:
            for r in analysis.results:
                msg = "proven" if r.success else "failed"
                print(f"{analysis.filename_short}: {r.property_name}: {msg}")
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

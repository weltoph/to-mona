#!python3
from parser import parse_file
from mona import write_tmp_file, call_mona, MonaError
from rendering import render_property_unreachability, render_base_theory

import argparse

parser = argparse.ArgumentParser()

parser.add_argument("file",
        help="file to be processed",
        nargs="+")

parser.add_argument("-v",
        help="increases verbosity (ranges from only report errors to chatty)",
        action="count",
        default=0)

parser.add_argument("-q",
        help="decreases verbosity (ranges from only report errors to chatty)",
        action="count",
        default=0)

args = parser.parse_args()
verbosity = max(0, min(2, 1 + args.v - args.q))

for filename in args.file:
    if 1 < verbosity:
        print(f"parsing {filename}...")
    system = parse_file(filename)
    if 1 < verbosity:
        print(f"constructing base theory for system form {filename}...")
    base_theory = render_base_theory(system)
    for property_name in system.property_names:
        if 1 < verbosity:
            print(f"attempting to prove unreachability of {property_name}:")
        proof_script = write_tmp_file(
                render_property_unreachability(system, property_name,
                    cached_base_theory=base_theory))
        if 1 < verbosity:
            print(f"created proof script {proof_script}")
        try:
            result = call_mona(proof_script)
        except MonaError as mona_error:
            print(f"Mona failed with the following error: {mona_error}")
        else:
            provable = "Formula is unsatisfiable" in result
            if provable:
                if 0 < verbosity:
                    print(f"{filename}: Unreachability of {property_name}" +
                    " could be proven")
            else:
                print(f"{filename}: Unreachability of {property_name} could"
                        + " not be proven")

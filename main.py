#!python3
from parser import parse_file
from mona import write_tmp_file, call_mona, MonaError
from rendering import render_property_unreachability, render_base_theory

import datetime

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


parser.add_argument("-s",
        help="outputs statistics only",
        action="store_true")

args = parser.parse_args()
verbosity = max(0, min(2, 1 + args.v - args.q)) if not args.s else -1

filename_column = "Filename:" + " "*11
property_column = "Property:" + " "*11
time_column     = "Time:"     + " "*15
header = f"{filename_column}|{property_column}|{time_column}"
if args.s:
    print(header)
    print("="*(3*20 + 2))

for filename in args.file:
    if 1 < verbosity:
        print(f"parsing {filename}...")
    system = parse_file(filename)
    if 1 < verbosity:
        print(f"constructing base theory for system form {filename}...")
    begin = datetime.datetime.now()
    base_theory = render_base_theory(system)
    delta_base_theory = datetime.datetime.now() - begin
    for property_name in system.property_names:
        if 1 < verbosity:
            print(f"attempting to prove unreachability of {property_name}:")
        begin = datetime.datetime.now()
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
            delta_property_proof = datetime.datetime.now() - begin
            if args.s:
                filename_column_instance = (" "*(20 - len(filename))
                        + filename[-20:])
                property_column_instance = (" "*(20 - len(property_name))
                        + property_name[:20])
                bt = str(delta_base_theory.total_seconds())[:7]
                bt = bt + '0'*(7 - len(bt))
                pp = str(delta_property_proof.total_seconds())[:7]
                pp = pp + '0'*(7 - len(pp))
                time_delta = f"{bt}s + {pp}s"
                time_column_instance = " "*(20 - len(time_delta)) + time_delta
                print(f"{filename_column_instance}|{property_column_instance}|"
                        + f"{time_column_instance}")
            if provable:
                if 0 < verbosity:
                    print(f"{filename}: Unreachability of {property_name}" +
                    " could be proven")
            else:
                if 0 <= verbosity:
                    print(f"{filename}: Unreachability of {property_name}"
                        + " could not be proven")

# Experiments

To run the experiments it is necessary to have a working python3-environment
with the packages `lark-parser` and `jinja2`. Furthermore, `mona` has to be
in `PATH`.

Then one can simply run `python main.py -s examples/*`.

A Dockerfile is provided for convenience.

Additionally, one may execute the `get-mona-time.sh` script with argument
`examples/wave-tree.mona` to get the timing of the deadlock proof for the
Dijkstra-Scholten algorithm on tree structures.

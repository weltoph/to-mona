# Experiments

To run the experiments it is necessary to have a working python3-environment
with the packages `lark-parser` and `jinja2`. Furthermore, `mona` has to be
in `PATH`.

Then one can simply run
```
python main.py -s\
  ./examples/left-hander-philosopher.sys\
  ./examples/left-hander-philosopher-remembering-forks.sys\
  ./examples/two-global-forks.sys\
  ./examples/exclusive-task.sys\
  ./examples/semaphore.sys\
  ./examples/burns.sys\
  ./examples/preemptive-task-arbitrary.sys\
  ./examples/preemptive-task-highest.sys\
  ./examples/dijkstra-scholten.sys
```

A Dockerfile is provided for convenience which runs above command by default.

Additionally, one may execute the `get-mona-time.sh` script with argument
`examples/wave-tree.mona` to get the timing of the deadlock proof for the
Dijkstra-Scholten algorithm on tree structures. (Or simply execute
`time mona examples/wave-tree.mona` and interpret the results oneself.)

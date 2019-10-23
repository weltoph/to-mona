from lark import Lark, Transformer

from system import Component, System
from formula import *
from bounded import *
from mona import theory

class ParserError(Exception):
    pass

grammar = """
    start: component+ formula
    component: "Component" NAME initial_state transition+ [critical_states]
    ?initial_state: "initial" NAME ";"
    ?critical_states: "critical" state_list ";"

    state_list: state | state "," state_list
    state: NAME
    transition: NAME "->" NAME "->" NAME ";"

    formula: "Formula" clause+
    clause: "ex" var_list ":" comparison_formula "." ports ["with" broadcasts]";"

    broadcasts: broadcast | [broadcast "&"]+ broadcast
    broadcast: "all" variable ":" comparison_formula "." port

    ports: port | [port "&"]+ port
    port: NAME "(" (term | constant) ")"

    comparison_formula: [comparison_atom "&"] comparison_atom | "true"
    ?comparison_atom: term comparison term | constant comparison term | term comparison constant

    ?comparison: smaller | equal | unequal | bigger | smaller_equal | bigger_equal

    smaller: "<"
    equal: "="
    unequal: "~="
    bigger: ">"
    smaller_equal: "<="
    bigger_equal: "=>"

    ?term: variable | successor
    successor: "succ(" term ")"

    constant: INT

    var_list: variable | [variable ","]+ variable
    variable: NAME

    COMMENT: "#" /.*/ NEWLINE

    %import common.INT
    %import common.CNAME -> NAME
    %import common.WS
    %import common.NEWLINE
    %ignore WS
    %ignore COMMENT
"""

parser = Lark(grammar)

class Transformation(Transformer):
    def __init__(self):
        self.components = []
        self.clause_index = 0
        self.broadcast_index = 0

    def transition(self, args):
        return (str(args[0]), str(args[1]), str(args[2]))

    def component(self, args):
        name = str(args.pop(0))
        initial = str(args.pop(0))
        if type(args[-1]) is list:
            critical_states = args.pop()
        else:
            critical_states = []
        transitions = args
        component = Component(name, initial, transitions, critical_states)
        self.components.append(component)
        return component

    def variable(self, args):
        name = str(args[0])
        return Variable(name)

    def successor(self, args):
        var = args.pop()
        return Successor(var)

    def smaller(self, _):
        return Smaller

    def bigger(self, _):
        return Bigger

    def smaller_equal(self, _):
        return SmallerEqual

    def bigger_equal(self, _):
        return BiggerEqual

    def equal(self, _):
        return Equal

    def unequal(self, _):
        return Unequal

    def comparison_atom(self, args):
        left = args.pop(0)
        comparison = args.pop(0)
        right = args.pop(0)
        return comparison(left, right)

    def comparison_formula(self, args):
        if not args:
            return Guard([])
        else:
            return Guard(args)

    def var_list(self, args):
        return args

    def port(self, args):
        port_name = str(args.pop(0))
        argument = args.pop(0)
        p = Port(port_name, argument)
        return p

    def ports(self, args):
        return args

    def broadcast(self, args):
        var = args.pop(0)
        guard = args.pop(0)
        port = args.pop(0)
        broadcast = Broadcast(var, guard, port, self.broadcast_index)
        self.broadcast_index += 1
        return broadcast

    def clause(self, args):
        variables = args.pop(0)
        guard = args.pop(0)
        ports = args.pop(0)
        if args and type(args[0]):
            broadcasts = args.pop(0).children
        else:
            broadcasts = []
        clause = Clause(variables, guard, ports, broadcasts, self.clause_index)
        self.clause_index += 1
        self.broadcast_index = 0
        return clause

    def formula(self, args):
        return Interaction(args)

    def constant(self, args):
        return Constant(int(args.pop()))

    def start(self, args):
        components = args[:-1]
        system = System(components)
        formula = args[-1]
        bounded_formula = BoundedInteraction.bind_to(formula, system)
        return bounded_formula

    def state(self, args):
        return [str(args.pop())]

    def state_list(self, args):
        if len(args) == 1:
            return args.pop()
        else:
            new_state = args.pop(0)
            others = args.pop(0)
            return [new_state] + others

def parse(filename: str) -> BoundedInteraction:
    with open(filename, "r") as f:
        text = f.read()
        tree = parser.parse(text)
        system = Transformation().transform(tree)
        return system

if __name__ == "__main__":
    import sys
    with open(sys.argv[1], "r") as f:
        text = f.read()
        tree = parser.parse(text)
        bounded_formula = Transformation().transform(tree)
        theory_script = theory(bounded_formula)
        print(theory_script)

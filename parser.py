from lark import Lark, Transformer

from system import Component, System
from formula import *
from bounded import *

class ParserError(Exception):
    pass

grammar = """
    system: components interaction            -> system
          | components interaction properties -> system_with_custom_properties

    components: component (component)*

    properties: custom_property (custom_property)*

    custom_property: "property" STRING "{" STRING "}"

    component: "Component" COMPONENTNAME "<" STATENAME ">" "{" transition (transition)* "}"
    transition: STATENAME "->" STATENAME "->" STATENAME

    COMPONENTNAME: COMPNAME
    STATENAME: COMPNAME

    COMPNAME: /[a-zA-Z][a-zA-Z0-9]*/

    interaction: "Formula" "{" clause (";" clause)* ";"? "}"

    clause: clause_body              -> local_clause
          | clause_body (broadcast)+ -> mixed_clause
          | (broadcast)+             -> broadcasting_clause

    clause_body: conjunctive_guard "." predicate_conjunction -> guarded_clause_body
               | predicate_conjunction                       -> unguarded_clause_body

    broadcast: "broadcasting" "{" variable ":" broadcast_body "}"

    broadcast_body: generell_guard "." predicate_disjunction -> guarded_broadcast
                  | predicate_disjunction                    -> unguarded_broadcast

    generell_guard: restriction "&" restriction -> comparison_conjunct
                  | restriction "|" restriction -> comparison_disjunct
                  | restriction                 -> comparison_atom

    conjunctive_guard: restriction ("&" restriction)*

    restriction: term comparison_symbol term -> comparison
               | "last0(" term ")"           -> last_left
               | "last1(" term ")"           -> last_right

    comparison_symbol: "~=" -> neq
                     | "="  -> eq
                     | "<"  -> lt
                     | "<=" -> leq
                     | ">"  -> gt
                     | ">=" -> geq

    predicate_conjunction: predicate ("&" predicate)*
    predicate_disjunction: predicate ("|" predicate)*

    predicate: NAME "(" term ")"

    term: left_succ
        | right_succ
        | variable
        | constant

    variable: NAME

    left_succ:  "succ0(" term ")"
    right_succ: "succ1(" term ")"
    constant: INT

    NAME: /(?!(succ0|succ1|last0|last1))[a-zA-Z][a-zA-Z0-9]*/
    COMMENT: "#" /.*/ NEWLINE

    %import common.INT
    %import common.ESCAPED_STRING -> STRING
    %import common.WS
    %import common.NEWLINE
    %ignore WS
    %ignore COMMENT
"""

parser = Lark(grammar, start="system")

if __name__ == "__main__":
    import sys
    files = [filename for filename in sys.argv[1:] if filename[-3:] == "sys"]
    for filename in files:
        try:
            with open(filename, "r") as f:
                text = f.read()
                tree = parser.parse(text)
                print(tree)
        except IsADirectoryError:
            continue

from lark import Lark, Transformer, v_args
from rendering import render_base_theory

class ParserError(Exception):
    pass

grammar = """
    system: components interaction                -> plain_system
          | components interaction mona_additions -> restricted_system

    components: component (component)*

    mona_additions: (custom_property|custom_assumption) (custom_property|custom_assumption)*

    custom_property: "property" STRING "{" STRING "}"

    custom_assumption: "assumption" STRING "{" STRING "}"

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

    generell_guard: conjunctive_guard ("|" conjunctive_guard)*

    conjunctive_guard: restriction ("&" restriction)*

    restriction: term COMPARISONSYMBOL term -> comparison
               | "last(" term ")"           -> last

    COMPARISONSYMBOL: "~=" | "=" | "<" | "<=" | ">" | ">="

    predicate_conjunction: predicate ("&" predicate)*
    predicate_disjunction: predicate ("|" predicate)*

    predicate: NAME "(" term ")"

    ?term: succ
         | variable
         | constant

    variable: NAME

    succ:  "succ(" term ")"
    constant: INT

    NAME: /(?!(succ|last))[a-zA-Z][a-zA-Z0-9]*/
    COMMENT: "#" /.*/ NEWLINE

    %import common.INT
    %import common.ESCAPED_STRING -> STRING
    %import common.WS
    %import common.NEWLINE
    %ignore WS
    %ignore COMMENT
"""

parser = Lark(grammar, start="system")

class TermParser(Transformer):
    @v_args(inline=True)
    def constant(self, value):
        from formula import Constant
        return Constant(value)

    @v_args(inline=True)
    def succ(self, term):
        from formula import Successor
        return Successor(term)

    @v_args(inline=True)
    def variable(self, name):
        from formula import Variable
        return Variable(str(name))

class PredicateParser(Transformer):
    @v_args(inline=True)
    def predicate(self, name, argument):
        from formula import Predicate
        return Predicate(str(name), argument)

    def predicate_conjunction(self, predicates):
        from formula import PredicateConjunction
        return PredicateConjunction(set(predicates))

    def predicate_disjunction(self, predicates):
        from formula import PredicateDisjunction
        return PredicateDisjunction(set(predicates))

class RestrictionParser(Transformer):
    @v_args(inline=True)
    def comparison(self, left, symbol, right):
        from formula import Below, BelowEqual, Above, AboveEqual
        from formula import Equal, Unequal
        lookup = {
                "~=": Unequal,
                "=" : Equal,
                "<" : Below,
                "<=": BelowEqual,
                ">" : Above,
                ">=": AboveEqual,
                }
        return lookup[str(symbol)](left, right)

    @v_args(inline=True)
    def last(self, argument):
        from formula import Last
        return Last(argument)

class GuardParser(Transformer):
    def conjunctive_guard(self, restrictions):
        from formula import RestrictionConjunction
        return RestrictionConjunction(restrictions)

    def generell_guard(self, conjunctions):
        from formula import RestrictionDisjunction
        return RestrictionDisjunction(conjunctions)

class BroadcastParser(Transformer):
    @v_args(inline=True)
    def unguarded_broadcast(self, disjunction):
        from formula import RestrictionConjunction, RestrictionDisjunction
        return (RestrictionDisjunction([RestrictionConjunction([])]),
            disjunction)

    @v_args(inline=True)
    def guarded_broadcast(self, guard, disjunction):
        return (guard, disjunction)

    @v_args(inline=True)
    def broadcast(self, variable, body):
        from formula import Broadcast
        return Broadcast(variable, *body)

class ClauseParser(Transformer):
    @v_args(inline=True)
    def unguarded_clause_body(self, conjunction):
        from formula import RestrictionConjunction
        return (RestrictionConjunction([]), conjunction)

    @v_args(inline=True)
    def guarded_clause_body(self, guard, conjunction):
        return (guard, conjunction)

    @v_args(inline=True)
    def local_clause(self, body):
        from formula import Clause
        return Clause(*body, [])

    @v_args(inline=True)
    def mixed_clause(self, body, *broadcasts):
        from formula import Clause
        return Clause(*body, broadcasts)

    def broadcasting_clause(self, broadcasts):
        from formula import Clause, RestrictionConjunction
        from formula import PredicateConjunction
        return Clause(RestrictionConjunction([]), PredicateConjunction(set()),
                broadcasts)

    def interaction(self, clauses):
        return clauses

class ComponentParser(Transformer):
    @v_args(inline=True)
    def transition(self, source, port, target):
        return (str(source), str(port), str(target))

    @v_args(inline=True)
    def component(self, name, initial, *transitions):
        from system import Component
        return Component(name, initial, transitions)

    def components(self, components):
        return components

class PropertyParser(Transformer):
    @v_args(inline=True)
    def custom_property(self, name, value):
        from system import SystemAddition
        return (SystemAddition.PROPERTY, str(name)[1:-1], str(value)[1:-1])

    @v_args(inline=True)
    def custom_assumption(self, name, value):
        from system import SystemAddition
        return (SystemAddition.ASSUMPTION, str(name)[1:-1], str(value)[1:-1])

    def mona_additions(self, additions):
        return additions

class SystemParser(Transformer):
    @v_args(inline=True)
    def plain_system(self, components, interaction):
        from system import System
        return System(components, interaction, {}, {})

    @v_args(inline=True)
    def restricted_system(self, components, interaction, additions):
        from system import System, SystemAddition
        return System(components, interaction,
                {name: value for kind, name, value in additions
                    if kind == SystemAddition.ASSUMPTION},
                {name: value for kind, name, value in additions
                    if kind == SystemAddition.PROPERTY})


if __name__ == "__main__":
    import sys
    files = [filename for filename in sys.argv[1:] if filename.endswith(".sys")]
    for filename in files:
        try:
            print(filename)
            with open(filename, "r") as f:
                text = f.read()
                transformer = (TermParser() * PredicateParser()
                        * RestrictionParser() * GuardParser()
                        * BroadcastParser() * ClauseParser()
                        * ComponentParser() * PropertyParser()
                        * SystemParser())
                system = transformer.transform(parser.parse(text))
                print(render_base_theory(system))
        except IsADirectoryError:
            continue

from lark import Lark, Transformer, v_args

class ParserError(Exception):
    pass

grammar = """
    system: components interaction                -> plain_system
          | components interaction mona_additions -> restricted_system

    components: component (component)*

    mona_additions: mona_addition (mona_addition)*

    mona_addition: (custom_property|custom_assumption) (custom_property|custom_assumption)*

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
               | "last0(" term ")"          -> last_left
               | "last1(" term ")"          -> last_right

    COMPARISONSYMBOL: "~=" | "=" | "<" | "<=" | ">" | ">="

    predicate_conjunction: predicate ("&" predicate)*
    predicate_disjunction: predicate ("|" predicate)*

    predicate: NAME "(" term ")"

    ?term: left_succ
         | right_succ
         | variable
         | constant

    variable: NAME

    left_succ:  "succ0(" term ")"
    right_succ: "succ1(" term ")"
    constant: "root"                              -> constant_root
            | constant "."  CONSTANT_PROLONGATION -> constant_term

    CONSTANT_PROLONGATION: ("0"|"1")

    NAME: /(?!(succ0|succ1|last0|last1|root))[a-zA-Z][a-zA-Z0-9]*/
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
    def constant_root(self):
        from formula import Constant
        return Constant("root")

    @v_args(inline=True)
    def constant_term(self, current, prolongation):
        from formula import Constant
        return Constant(f"{current.value}.{str(prolongation)}")

    @v_args(inline=True)
    def left_succ(self, term):
        from formula import Successor
        return Successor(0, term)

    @v_args(inline=True)
    def right_succ(self, term):
        from formula import Successor
        return Successor(1, term)

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
    def last_left(self, argument):
        from formula import Last
        return Last(0, argument)

    @v_args(inline=True)
    def last_right(self, argument):
        from formula import Last
        return Last(1, argument)

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

if __name__ == "__main__":
    import sys
    files = [filename for filename in sys.argv[1:] if filename[-3:] == "sys"]
    for filename in files:
        try:
            print(filename)
            with open(filename, "r") as f:
                text = f.read()
                transformer = (TermParser() * PredicateParser()
                        * RestrictionParser() * GuardParser()
                        * BroadcastParser() * ClauseParser())
                tree = transformer.transform(parser.parse(text))
                print(tree.pretty())
        except IsADirectoryError:
            continue

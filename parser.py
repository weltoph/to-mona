import lark  # type: ignore
import system
import logging
import formula


logger = logging.getLogger(__name__)


class ParserError(Exception):
    pass


grammar_file = "language-spec.lark"
logger.debug(f"Instantiating parser from {grammar_file}")
parser = lark.Lark(open(grammar_file))


class FormulaParser(lark.Transformer):
    def __init__(self, system):
        self.system = system
        self.assumptions = {}
        self.properties = {}
        self.clauses = []

    @property
    def final_interaction(self) -> formula.Interaction:
        return formula.Interaction(self.clauses,
                                   self.system,
                                   self.assumptions,
                                   self.properties)

    @lark.v_args(inline=True)
    def constant(self, value):
        from formula import Constant
        logger.debug(f"Parsing constant value {str(value)}")
        return Constant(self.system, int(value))

    @lark.v_args(inline=True)
    def succ(self, term):
        from formula import Successor
        logger.debug(f"Parsing successor term with argument {term}")
        return Successor(self.system, term)

    @lark.v_args(inline=True)
    def variable(self, name):
        from formula import Variable
        logger.debug(f"Parsing variable term with name {str(name)}")
        return Variable(self.system, str(name))

    @lark.v_args(inline=True)
    def predicate(self, name, argument):
        from formula import Predicate
        edge = self.system.edge_with_label(str(name))
        if not edge:
            raise ParserError("Cannot bind Predicate {str(name)}")
        logger.debug(f"Parsing predicate bound to {edge} named {str(name)}")
        return Predicate(self.system, str(name), argument, *edge)

    def predicate_conjunction(self, predicates):
        from formula import PredicateConjunction
        logger.debug(f"Parsing conjunction of predicates {predicates}")
        return PredicateConjunction(self.system, frozenset(predicates))

    def predicate_disjunction(self, predicates):
        from formula import PredicateDisjunction
        logger.debug(f"Parsing disjunction of predicates {predicates}")
        return PredicateDisjunction(self.system, frozenset(predicates))

    @lark.v_args(inline=True)
    def comparison(self, left, symbol, right):
        from formula import Less, LessEqual, Equal, Unequal
        if symbol == "~=":
            result = Unequal(self.system, left, right)
        elif symbol == "=":
            result = Equal(self.system, left, right)
        elif symbol == "<":
            result = Less(self.system, left, right)
        elif symbol == "<=":
            result = LessEqual(self.system, left, right)
        elif symbol == ">":
            result = Less(self.system, right, left)
        elif symbol == ">=":
            result = LessEqual(self.system, right, left)
        else:
            raise ParserError(f"Unrecognised comparison {symbol}")
        logger.debug(f"Parsing comparison {result}")
        return result

    @lark.v_args(inline=True)
    def last(self, argument):
        from formula import Last
        logger.debug(f"Parsing last term with argument {argument}")
        return Last(self.system, argument)

    def conjunctive_guard(self, restrictions):
        from formula import RestrictionCollection
        logger.debug(f"Parsing conjunction of restrictions {restrictions}")
        res = RestrictionCollection(self.system,
                                    frozenset({r for r in restrictions}))
        logger.debug(f"returning {res} of type {type(res)}")
        return res

    def generell_guard(self, conjunctions):
        from formula import RestrictionCollection
        logger.debug(f"Parsing disjunction of conjunctions {conjunctions}")
        gathered_conjunctions = frozenset(conjunctions)
        return RestrictionCollection(self.system, gathered_conjunctions)

    @lark.v_args(inline=True)
    def unguarded_broadcast(self, disjunction):
        from formula import RestrictionCollection
        logger.debug(
                f"Parsing unguarded broadcast of predicates {disjunction}")
        return (RestrictionCollection(self.system,
                                      frozenset({RestrictionCollection(
                                          self.system, frozenset())})),
                disjunction)

    @lark.v_args(inline=True)
    def guarded_broadcast(self, guard, disjunction):
        logger.debug(f"Parsing guarded broadcast with guard {guard}"
                     + " and " + f"predicates {disjunction}")
        return (guard, disjunction)

    @lark.v_args(inline=True)
    def broadcast(self, variable, body):
        from formula import Broadcast
        logger.debug(f"Parsing broadcast with variable {variable}"
                     + " and " + f"body {body}")
        return Broadcast(self.system, variable, *body)

    @lark.v_args(inline=True)
    def unguarded_clause_body(self, conjunction):
        from formula import RestrictionCollection
        logger.debug("Parsing unguarded clause body with conjunction "
                     + " " + str(conjunction))
        return (RestrictionCollection(self.system, frozenset()), conjunction)

    @lark.v_args(inline=True)
    def guarded_clause_body(self, guard, conjunction):
        logger.debug(f"Parsing guarded clause body with guard {guard}"
                     + " and " + f"conjunction {conjunction}")
        return (guard, conjunction)

    @lark.v_args(inline=True)
    def local_clause(self, body):
        from formula import Clause
        logger.debug(f"Parsing local clause with body {body}")
        self.clauses.append(Clause(self.system, *body, []))
        raise lark.Discard()

    @lark.v_args(inline=True)
    def mixed_clause(self, body, *broadcasts):
        from formula import Clause
        logger.debug(f"Parsing mixed clause with {body} and {broadcasts}")
        self.clauses.append(Clause(self.system, *body, broadcasts))
        raise lark.Discard()

    def broadcasting_clause(self, broadcasts):
        from formula import Clause, RestrictionCollection
        from formula import PredicateConjunction
        logger.debug(f"Parsing broadcasting clause {broadcasts}")
        self.clauses.append(Clause(self.system,
                                   RestrictionCollection(self.system,
                                                         frozenset()),
                                   PredicateConjunction(self.system,
                                                        frozenset()),
                                   broadcasts))
        raise lark.Discard()

    @lark.v_args(inline=True)
    def custom_property(self, name, value):
        logger.debug(f"Parsing custom property {str(name)}: {str(value)}")
        self.properties[str(name)[1:-1]] = str(value)[1:-1]
        raise lark.Discard()

    @lark.v_args(inline=True)
    def custom_assumption(self, name, value):
        logger.debug(f"Parsing custom assumption {str(name)}: {str(value)}")
        self.assumptions[str(name)[1:-1]] = str(value)[1:-1]
        raise lark.Discard()


class ComponentParser(lark.Transformer):
    def __init__(self):
        self.values = []

    @lark.v_args(inline=True)
    def transition(self, source, port, target):
        transition = (str(source), str(port), str(target))
        logger.debug(f"Parsing transition {transition}")
        return transition

    @lark.v_args(inline=True)
    def component(self, name, initial, *transitions):
        from system import Component
        self.values.append(Component(str(name), str(initial),
                           frozenset(transitions)))
        raise lark.Discard()


def parse_file(filename) -> formula.Interaction:
    with open(filename, "r") as f:
        logger.debug(f"begin parsing of {filename}")
        text = f.read()
        components = ComponentParser()
        formula_tree = components.transform(parser.parse(text))
        parsed_system = system.System(frozenset(components.values))
        clause_parser = FormulaParser(parsed_system)
        clause_parser.transform(formula_tree)
        logger.info(f"successfully parsed {filename}")
        return clause_parser.final_interaction

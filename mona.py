from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass

import formula

class MonaError(Exception):
    pass

class Formula(object):
    def render(self) -> str:
        raise NotImplemented

class Term(object):
    def render(self) -> str:
        raise NotImplemented

@dataclass
class Variable(Term):
    name: str

    def render(self) -> str:
        return self.name

@dataclass
class Constant(Term):
    value: int

    def render(self) -> str:
        return self.value

@dataclass
class StatementChain(Formula):
    statements: List[Formula]

    def render(self) -> str:
        if not self.statements:
            return f"( {self.empty_value} )"
        statements = f" {self.comp_symb} ".join(
                [s.render() for s in self.statements])
        return f"( {statements} )"

@dataclass
class Conjunction(StatementChain):
    @property
    def comp_symb(self) -> str:
        return "&"

    @property
    def empty_value(self):
        return "true"

@dataclass
class Disjunction(StatementChain):
    @property
    def comp_symb(self) -> str:
        return "|"

    @property
    def empty_value(self):
        return "false"

@dataclass
class Implication(Formula):
    left: Formula
    right: Formula

    def render(self) -> str:
        return f"( ({self.left.render()}) => ({self.right.render()}) )"

@dataclass
class Negation(Formula):
    inner: Formula

    def render(self) -> str:
        return f"~({self.inner.render()})"

@dataclass
class Atom(Formula):
    pass

@dataclass
class Comparison(Atom):
    left: Term
    right: Term

    def __post_init__(self):
        self.left = (Variable(self.left) if type(self.left) is str
                else self.left)
        self.right = (Variable(self.right) if type(self.right) is str
                else self.right)

    def render(self) -> str:
        return f"({self.left.render()} {self.comp_symb} {self.right.render()})"

@dataclass
class Unequal(Comparison):
    @property
    def comp_symb(self) -> str:
        return "~="

@dataclass
class Equal(Comparison):
    @property
    def comp_symb(self) -> str:
        return "="

@dataclass
class Less(Comparison):
    @property
    def comp_symb(self) -> str:
        return "<"

@dataclass
class LessEqual(Comparison):
    @property
    def comp_symb(self) -> str:
        return "<="

@dataclass
class Greater(Comparison):
    @property
    def comp_symb(self) -> str:
        return ">"

@dataclass
class GreaterEqual(Comparison):
    @property
    def comp_symb(self) -> str:
        return ">="



@dataclass
class Participation(Atom):
    first_order: Union[Variable, str]
    second_order: Union[Variable, str]

    def __post_init__(self):
        self.first_order = (
                Variable(self.first_order) if type(self.first_order) is str
                else self.first_order)
        self.second_order = (
                Variable(self.second_order) if type(self.second_order) is str
                else self.second_order)


    def render(self) -> str:
        return f"{self.first_order.render()} {self.part_symb} {self.second_order.render()}"

@dataclass
class ElementIn(Participation):
    @property
    def part_symb(self) -> str:
        return "in"

@dataclass
class ElementNotIn(Participation):
    @property
    def part_symb(self) -> str:
        return "notin"

@dataclass
class PredicateCall(Atom):
    name: str
    variables: Union[List[Union[Variable, str]], Union[Variable, str]]

    def __post_init__(self):
        self.variables = (self.variables if type(self.variables) == list
                else [self.variables])
        self.variables = [
                (Variable(v) if type(v) is str else v)
                for v in self.variables]

    def render(self) -> str:
        variables = ", ".join([v.render() for v in self.variables])
        return f"{self.name}({variables})"

@dataclass
class Quantification(Formula):
    variables: Union[List[Union[Variable, str]], Union[Variable, str]]
    inner: Formula

    def __post_init__(self):
        self.variables = (self.variables if type(self.variables) is list
                else [self.variables])
        self.variables = [
                (Variable(v) if type(v) is str else v)
                for v in self.variables]

    def render(self) -> str:
        if not self.variables:
            return f"( {self.render_inner()} )"
        variables = ", ".join([v.render() for v in self.variables])
        quantification = f"{self.kind}{self.order} {variables}"
        return f"{quantification}: ( {self.render_inner()} )"

    def render_inner(self) -> str:
        return self.inner.render()

@dataclass
class ExistentialSecondOrder(Quantification):
    @property
    def kind(self) -> str:
        return "ex"

    @property
    def order(self) -> str:
        return "2"

@dataclass
class ExistentialFirstOrder(Quantification):
    @property
    def kind(self) -> str:
        return "ex"

    @property
    def order(self) -> str:
        return "1"

    def render_inner(self) -> str:
        guards = Conjunction([LessEqual(Constant(0), v)
            for v in self.variables] + [Less(v, "n") for v in self.variables])
        return f"({guards.render()}) & ({self.inner.render()})"

@dataclass
class UniversalSecondOrder(Quantification):
    @property
    def kind(self) -> str:
        return "all"

    @property
    def order(self) -> str:
        return "2"

@dataclass
class UniversalFirstOrder(Quantification):
    @property
    def kind(self) -> str:
        return "all"

    @property
    def order(self) -> str:
        return "1"

    def render_inner(self) -> str:
        guards = Conjunction([LessEqual(Constant(0), v)
            for v in self.variables] + [Less(v, "n") for v in self.variables])
        if guards:
            return f"({guards.render()}) => ({self.inner.render()})"
        else:
            return f"({self.inner.render()})"

@dataclass
class PredicateDefinition(Formula):
    name: str
    second_order: List[Union[Variable, str]]
    first_order: List[Union[Variable, str]]
    inner: Formula

    def __post_init__(self):
        self.second_order = [
                (Variable(v) if type(v) is str else v)
                for v in self.second_order]
        self.first_order = [
                (Variable(v) if type(v) is str else v)
                for v in self.first_order]

    @property
    def variable_list(self) -> str:
        return ", ".join([f"var2 {v.render()}" for v in self.second_order]
                + [f"var1 {v.render()}" for v in self.first_order])

    def render(self) -> str:
        return (f"pred {self.name}({self.variable_list}) = (\n"
                + f"{self.inner.render()}\n"
                + f");")

def translate_term(term: formula.Term) -> Term:
    if type(term) is formula.Constant:
        return Constant(term.value)
    elif type(term) is formula.Variable:
        return Variable(term.name)
    elif type(term) is formula.Successor:
        current_term = term.argument
        prefix = "succ_"
        while type(current_term) is formula.Successor:
            prefix += "succ_"
            current_term = current_term.argument
        if type(current_term) is formula.Constant:
            return Variable(f"{prefix}{current_term.value}")
        elif type(current_term) is formula.Variable:
            return Variable(f"{prefix}{current_term.name}")
    else:
        raise MonaError("Cannot translate {term} to ws1s")

def successor_constraint(succ: formula.Successor) -> PredicateCall:
    term_var = translate_term(succ)
    argument_var = translate_term(succ.argument)
    return PredicateCall("is_next", [argument_var, term_var])

def translate_formula(f: formula.Formula) -> Formula:
    if type(f) is formula.Last:
        argument = translate_term(formula.argument)
        return PredicateCall("is_last", argument)
    elif type(f) is formula.Less:
        left = translate_term(f.left)
        right = translate_term(f.right)
        return Less(left, right)
    elif type(f) is formula.LessEqual:
        left = translate_term(f.left)
        right = translate_term(f.right)
        return LessEqual(left, right)
    elif type(f) is formula.Greater:
        left = translate_term(f.left)
        right = translate_term(f.right)
        return Greater(left, right)
    elif type(f) is formula.GreaterEqual:
        left = translate_term(f.left)
        right = translate_term(f.right)
        return GreaterEqual(left, right)
    elif type(f) is formula.Equal:
        left = translate_term(f.left)
        right = translate_term(f.right)
        return Equal(left, right)
    elif type(f) is formula.Unequal:
        left = translate_term(f.left)
        right = translate_term(f.right)
        return Unequal(left, right)
    elif type(f) is formula.RestrictionConjunction:
        return Conjunction([translate_formula(r) for r in f.restrictions])
    elif type(f) is formula.RestrictionDisjunction:
        return Disjunction([translate_formula(r) for r in f.restrictions])
    else:
        raise MonaError(f"Cannot translate {f} to ws1s")

def translate_guard_and_terms(guarded_statement:
        Union[formula.Broadcast, formula.Clause]):
    term_constraints = Conjunction([successor_constraint(t)
        for t in guarded_statement.local_terms if not t.is_atomic])
    guard = translate_formula(guarded_statement.guard)
    return Conjunction([guard, term_constraints])

def get_quantifiable_objects(statement:
        Union[formula.Broadcast, formula.Clause]):
    considered_terms = ([t for t in statement.local_terms if (not t.is_atomic)]
            + statement.local_variables)
    return [translate_term(t) for t in considered_terms]

from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass
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
        statements = f" {self.comp_symb} ".join(
                [s.render() for s in self.statements])
        return f"( {statements} )"

@dataclass
class Conjunction(StatementChain):
    @property
    def comp_symb(self) -> str:
        return "&"

@dataclass
class Disjunction(StatementChain):
    @property
    def comp_symb(self) -> str:
        return "|"

@dataclass
class BinaryConnective(Formula):
    left: Formula
    right: Formula

    def render(self) -> str:
        return f"( ({self.left.render()}) {self.conn_symb} ({self.right.render()}) )"

@dataclass
class Implication(BinaryConnective):
    @property
    def conn_symb(self) -> str:
        return "=>"

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
    variables: List[Union[Variable, str]]

    def __post_init__(self):
        self.variables = [
                (Variable(v) if type(v) is str else v)
                for v in self.variables]

    def render(self) -> str:
        variables = ", ".join([v.render() for v in self.variables])
        return f"{name}({variables})"

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
        variables = ", ".join([v.render() for v in self.variables])
        return f"{self.kind}{self.order} {variables}: ( {self.render_inner()} )"

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
        return f"({guards.render()}) => ({self.inner.render()})"

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
        return f"pred {self.name}({self.variable_list}) = (\n{self.inner.render()}\n);"

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

class MonaError(Exception):
    pass

class Formula(object):
    pass

class Term(object):
    def render(self) -> str:
        raise NotImplemented

@dataclass
class Variable(Term):
    name: str

    def render(self) -> str:
        return self.name

@dataclass
class StatementChain(Formula):
    statements: List[Formula]

    def render(self) -> str:
        statements = " {self.comp_symb} ".join(
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
        return "&"

@dataclass
class BinaryConnective(Formula):
    left: Formula
    right: Formula

    def render(self) -> str:
        return f"( ( {self.left.render()} ) {self.conn_symb} ( {self.right.render()} ) )"

@dataclass
class Implication(BinaryConnective):
    @property
    def conn_symb(self) -> str:
        return "=>"

@dataclass
class Negation(Formula):
    inner: Formula

    def render(self) -> str:
        return "~( {self.inner.render()} )"

@dataclass
class Atom(Formula):
    pass

@dataclass
class Participation(Atom):
    first_order: Variable
    second_order: Variable

    def render(self) -> str:
        return f"{self.first_order} {self.part_symb} {self.second_order}"

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
    variables: List[Variable]

    def render(self) -> str:
        variables = ", ".join([v.render() for v in self.variables])
        return f"{name}({variables})"

@dataclass
class Quantification(Formula):
    inner: Formula
    variables: List[Variable]

    def render(self) -> str:
        variables = ", ".join([v.render() for v in self.variables])
        return f"{kind}{order} {variables}: ( {self.inner.render()} )"

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

@dataclass
class PredicateDefinition(Formula):
    name: str
    inner: Formula
    second_order: List[Variable]
    first_order: List[Variable]

    def render(self) -> str:
        variables = ", ".join([f"var2 {v.render()}" for v in self.second_order]
                + [f"var1 {v.render()}" for v in self.first_order])
        return f"pred {self.name}({variables}) = ( {self.inner.render()} );"

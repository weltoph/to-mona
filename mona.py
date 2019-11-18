from typing import List, Tuple, Dict, Optional, Union, cast
from dataclasses import dataclass

VarStr = Union[str, "Variable"]

import formula

class MonaError(Exception):
    pass

class Formula(object):
    def render(self) -> str:
        raise NotImplementedError()

    def _block_indent(self, block: str) -> str:
        return "\n".join([f"  {l}" for l in block.split("\n")])

    def simplify(self) -> "Formula":
        return self

    def negate(self) -> "Formula":
        raise NotImplementedError(f"{type(self)} does not implement negate")

@dataclass
class RawFormula(Formula):
    formula: str

    def render(self) -> str:
        return self.formula

    def negate(self) -> "Formula":
        return Negation(self)

class Term(object):
    def render(self) -> str:
        raise NotImplementedError()

@dataclass
class Variable(Term):
    name: str

    def render(self) -> str:
        return self.name

@dataclass
class TermConstant(Term):
    value: int

    def render(self) -> str:
        return str(self.value)

@dataclass
class FormulaConstant(Formula):
    value: bool

    def render(self) -> str:
        if self.value:
            return "true"
        else:
            return "false"

    def negate(self) -> "FormulaConstant":
        return FormulaConstant(not self.value)

@dataclass
class StatementChain(Formula):
    statements: List[Formula]

    def __post_init__(self):
        self.comp_symb = ""

    def render(self) -> str:
        new_lines = []
        for s in self.statements:
            lines = s.render().split("\n")
            statement = [f"\t{l}" for l in lines]
            new_lines.append(self._block_indent(s.render()))
        inner = f"\n) {self.comp_symb} (\n".join(new_lines)
        return f"(\n{inner}\n)"

    def _simplified_statements(self) -> List[Formula]:
        return [s.simplify() for s in self.statements]

@dataclass
class Conjunction(StatementChain):
    def __post_init__(self):
        self.comp_symb = "&"

    def simplify(self):
        simplified = [s
                for s in self._simplified_statements()
                if not (type(s) is FormulaConstant and s.value)]
        if not simplified:
            return FormulaConstant(True)
        elif any([(type(s) is FormulaConstant and not s.value)
            for s in simplified]):
            return FormulaConstant(False)
        elif len(simplified) == 1:
                return simplified.pop()
        else:
            flatten = []
            for s in simplified:
                if type(s) == Conjunction:
                    flatten += s.statements
                else:
                    flatten.append(s)
            return Conjunction(flatten)

    def negate(self):
        return Disjunction([s.negate() for s in self.statements])

@dataclass
class Disjunction(StatementChain):
    def __post_init__(self):
        self.comp_symb = "|"

    def simplify(self):
        simplified = [s
                for s in self._simplified_statements()
                if not (type(s) is FormulaConstant and not s.value)]
        if not simplified:
            return FormulaConstant(False)
        elif any([(type(s) is FormulaConstant and s.value)
            for s in simplified]):
            return FormulaConstant(True)
        elif len(simplified) == 1:
                return simplified.pop()
        else:
            flatten = []
            for s in simplified:
                if type(s) == Disjunction:
                    flatten += s.statements
                else:
                    flatten.append(s)
            return Disjunction(flatten)

    def negate(self):
        return Conjunction([s.negate() for s in self.statements])

@dataclass
class Implication(Formula):
    left: Formula
    right: Formula

    def render(self) -> str:
        l = self._block_indent(self.left.render())
        r = self._block_indent(self.right.render())
        return f"(\n{l}\n) => (\n{r}\n)"

    def simplify(self):
        left = self.left.simplify()
        right = self.right.simplify()
        if type(left) is TermConstant:
            return right if left.value else TermConstant(True)
        elif type(right) is TermConstant:
            return TermConstant(True) if right.value else left.negate()
        elif type(right) is Implication:
            new_left = Conjunction([left, right.left]).simplify()
            new_right = right.right.simplify()
            return Implication(new_left, new_right)
        else:
            return Implication(left, right)

    def negate(self):
        return Conjunction([self.left, Negation(self.right)])

@dataclass
class Negation(Formula):
    inner: Formula

    def render(self) -> str:
        i = self._block_indent(self.inner.render())
        return f"~(\n{i}\n)"

    def simplify(self):
        return self.inner.negate().simplify()

    def negate(self):
        return self.inner

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
        self.comp_symb = ""

    def render(self) -> str:
        return f"{self.left.render()} {self.comp_symb} {self.right.render()}"

@dataclass
class Unequal(Comparison):
    def __post_init__(self):
        self.comp_symb = "~="

    def negate(self):
        return Equal(self.left, self.right)

@dataclass
class Equal(Comparison):
    def __post_init__(self):
        self.comp_symb = "="

    def negate(self):
        return Unequal(self.left, self.right)

@dataclass
class Less(Comparison):
    def __post_init__(self):
        self.comp_symb = "<"

    def negate(self):
        return LessEqual(self.right, self.left)

@dataclass
class LessEqual(Comparison):
    def __post_init__(self):
        self.comp_symb = "<="

    def negate(self):
        return Less(self.right, self.left)


@dataclass(init=False)
class Participation(Atom):
    first_order: Variable
    second_order: Variable

    def __init__(self,
                 first_order: Union[Variable, str],
                 second_order: Union[Variable, str]):
        if type(first_order) is str:
            self.first_order = Variable(cast(str, first_order))
        else:
            self.first_order = cast(Variable, first_order)
        if type(second_order) is str:
            self.second_order = Variable(cast(str, second_order))
        else:
            self.second_order = cast(Variable, second_order)

    def __post_init__(self):
        self.part_symb = ""

    def render(self) -> str:
        first = self.first_order.render()
        second = self.second_order.render()
        return f"{first} {self.part_symb} {second}"

@dataclass
class ElementIn(Participation):
    @property
    def part_symb(self) -> str:
        return "in"

    def negate(self):
        return ElementNotIn(self.first_order, self.second_order)

@dataclass
class ElementNotIn(Participation):
    @property
    def part_symb(self) -> str:
        return "notin"

    def negate(self):
        return ElementIn(self.first_order, self.second_order)

@dataclass(init=False)
class PredicateCall(Atom):
    name: str
    parameters: List[Union[Variable, TermConstant]]

    def __init__(self, name: str,
                 parameters: Union[List[VarStr], VarStr]):
        self.name = name
        if not type(self.parameters) is list:
            parameters = cast(List[VarStr], [parameters])
        self.parameters = [(Variable(cast(str, v)) if type(v) is str
                           else cast(Variable, v))
                          for v in self.parameters]

    def render(self) -> str:
        parameters = ", ".join([v.render() for v in self.parameters])
        return f"{self.name}({parameters})"

    def negate(self):
        return Negation(self)

@dataclass(init=False)
class Quantification(Formula):
    variables: List[Variable]
    inner: Formula

    def __init__(self, variables: Union[List[VarStr], VarStr], inner: Formula):
        if not type(self.variables) is list:
            variables = cast(List[VarStr], [variables])
        self.variables = [(Variable(cast(str, v)) if type(v) is str
                           else cast(Variable, v))
                          for v in self.variables]
        self.kind: str = ""


    def render(self) -> str:
        inner = self._block_indent(self._actual_inner().render())
        variables = ", ".join([v.name for v in self.variables])
        return f"{self.kind} {variables}: (\n{inner}\n)"

    def _actual_inner(self):
        return self.inner

    def simplify(self):
        inner = self.inner.simplify()
        if not self.variables:
            return inner
        else:
            return type(self)(self.variables, inner)

@dataclass
class GuardedFirstOrderQuantification(Quantification):
    def __post_init__(self):
        super().__post_init__()
        n = Variable("n")
        zero = TermConstant(0)
        self.guard = Conjunction([
                LessEqual(zero, v) for v in self.variables
            ] + [
                Less(v, n) for v in self.variables
            ])

@dataclass
class ExistentialSecondOrder(Quantification):
    def __post_init__(self):
        super().__post_init__()
        self.kind = "ex2"

    def negate(self):
        return UniversalSecondOrder(self.variables, self.inner.negate())

@dataclass
class ExistentialFirstOrder(GuardedFirstOrderQuantification):
    def __post_init__(self):
        super().__post_init__()
        self.kind = "ex1"

    def _actual_inner(self):
        return Conjunction([self.guard, self.inner]).simplify()

    def negate(self):
        return UniversalFirstOrder(self.variables, self.inner.negate())

@dataclass
class UniversalSecondOrder(Quantification):
    def __post_init__(self):
        super().__post_init__()
        self.kind = "all2"

    def negate(self):
        return ExistentialSecondOrder(self.variables, self.inner.negate())

@dataclass
class UniversalFirstOrder(GuardedFirstOrderQuantification):
    def __post_init__(self):
        super().__post_init__()
        self.kind = "all1"

    def _actual_inner(self):
        return Implication(self.guard, self.inner).simplify()

    def negate(self):
        return ExistentialFirstOrder(self.variables, self.inner.negate())

@dataclass(init=False)
class PredicateDefinition(Formula):
    name: str
    second_order: List[Variable]
    first_order: List[Variable]
    inner: Formula

    def __init__(self, name: str, second_order: Union[List[VarStr], VarStr],
                 first_order: Union[List[VarStr], VarStr], inner: Formula):
        self.name = name
        if not type(second_order) is list:
            second_order = cast(List[VarStr], [second_order])
        self.second_order = [(Variable(cast(str, v)) if type(v) is str
                              else cast(Variable, v))
                             for v in self.second_order]
        self.first_order = [(Variable(cast(str, v)) if type(v) is str
                             else cast(Variable, v))
                            for v in self.first_order]
        self.inner = inner

    def render(self) -> str:
        inner = self._block_indent(self.inner.render())
        variable_list = ", ".join([f"var2 {v.render()}" for v in self.second_order]
                + [f"var1 {v.render()}" for v in self.first_order])
        return f"pred {self.name}({variable_list}) = (\n{inner}\n);"

    def simplify(self):
        inner = self.inner.simplify()
        return PredicateDefinition(self.name, self.second_order,
                                   self.first_order, inner)


def translate_term(term: Union[formula.Variable,
                               formula.Successor]) -> Variable:
    if type(term) is formula.Variable:
        return Variable(cast(formula.Variable, term).name)
    elif type(term) is formula.Successor:
        current_term = cast(formula.Successor, term).argument
        prefix = "succ_"
        while type(current_term) is formula.Successor:
            prefix += "succ_"
            current_term = cast(formula.Successor, current_term).argument
        if type(current_term) is formula.Constant:
            current_term = cast(formula.Constant, current_term)
            return Variable(f"{prefix}{current_term.value}")
        elif type(current_term) is formula.Variable:
            current_term = cast(formula.Variable, current_term)
            return Variable(f"{prefix}{current_term.name}")
    raise MonaError("Cannot translate {term} to ws1s")

def successor_constraint(succ: formula.Successor) -> PredicateCall:
    term_var = cast(Variable, translate_term(succ))
    argument_var = translate_term(succ.argument)
    return PredicateCall("is_next", [argument_var, term_var])

def translate_formula(f: formula.Formula) -> Formula:
    if type(f) is formula.Last:
        f = cast(formula.Last, f)
        argument = translate_term(f.argument)
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

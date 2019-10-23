from dataclasses import dataclass, field
from typing import List, Iterable, Set, Dict, Optional

class FormulaError(Exception):
    pass

class Term(object):
    def __repr__(self):
        return f"{type(self)}<{self}>"

@dataclass
class Constant(Term):
    value: int

    @property
    def variables(self) -> Set["Variable"]:
        return set()

    @property
    def variable(self) -> Optional["Variable"]:
        return None

    def rename(self, renaming):
        return Constant(self.value)

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value

    def __str__(self):
        return str(self.value)

    @property
    def terms(self) -> List[Term]:
        return []

    @property
    def trivial_term(self) -> bool:
        return True

@dataclass
class Variable(Term):
    name: str

    @property
    def variables(self) -> Set["Variable"]:
        return {self}

    @property
    def variable(self) -> "Variable":
        return self

    def rename(self, renaming):
        return Variable(renaming.get(self.name, self.name))

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __str__(self):
        return self.name

    @property
    def terms(self) -> List[Term]:
        return [self]

    @property
    def trivial_term(self) -> bool:
        return True

@dataclass
class Successor(Term):
    argument: Term

    def __eq__(self, other):
        return type(self) == type(other) and self.argument == other.argument

    @property
    def trivial_term(self) -> bool:
        return False

    @property
    def variables(self) -> Set[Variable]:
        return {self.variable}

    @property
    def variable(self) -> Variable:
        return self.argument.variable

    def rename(self, renaming):
        return Successor(self.argument.rename(renaming))

    @property
    def terms(self) -> List[Term]:
        return [self] + self.argument.terms

    def __str__(self) -> str:
        return f"succ({self.argument})"

class Formula(object):
    def __repr__(self):
        return f"{type(self)}<{str(self)}>"

@dataclass
class Port(Formula):
    name: str
    argument: Term

    @property
    def variables(self) -> Set[Variable]:
        return {self.variable} if self.variable else set()

    @property
    def variable(self) -> Optional[Variable]:
        return self.argument.variable

    def rename(self, renaming):
        return Port(self.name, self.argument.rename(renaming))

    def __str__(self):
        return f"{self.name}({self.argument})"

    @property
    def terms(self) -> List[Term]:
        return self.argument.terms

@dataclass
class Comparison(Formula):
    left: Term
    right: Term

    @property
    def variables(self) -> Iterable[Variable]:
        return self.left.variables | self.right.variables

    @property
    def terms(self) -> Iterable[Term]:
        terms = [self.left, self.right]
        return [t for i, t in enumerate(terms) if not t in terms[:i]]

    def rename(self, renaming):
        return type(self)(self.left.rename(renaming),
                self.right.rename(renaming))

    def __str__(self):
        return f"{self.left} {self.comp_str} {self.right}"

@dataclass
class Smaller(Comparison):
    @property
    def comp_str(self):
        return "<"

@dataclass
class Bigger(Comparison):
    @property
    def comp_str(self):
        return ">"

@dataclass
class SmallerEqual(Comparison):
    @property
    def comp_str(self):
        return "<="

@dataclass
class BiggerEqual(Comparison):
    @property
    def comp_str(self):
        return ">="

@dataclass
class Equal(Comparison):
    @property
    def comp_str(self):
        return "="

@dataclass
class Unequal(Comparison):
    @property
    def comp_str(self):
        return "~="

class TrueGuard(Formula):
    def rename(self, renaming) -> "Guard":
        return TrueGuard()

    @property
    def variables(self) -> Iterable[Variable]:
        return set()

    @property
    def terms(self) -> List[Term]:
        return []

    @property
    def is_trivial(self) -> bool:
        return True

    def __str__(self):
        return "true"

@dataclass
class Guard(Formula):
    comparisons: List[Comparison]

    @property
    def is_trivial(self) -> bool:
        return not bool(self.comparisons)

    @property
    def variables(self) -> Iterable[Variable]:
        ret = set()
        for c in self.comparisons:
            ret |= c.variables
        return ret

    @property
    def terms(self) -> List[Term]:
        ret = []
        for c in self.comparisons:
            ret += c.terms
        return [t for i, t in enumerate(ret) if not t in ret[:i]]

    def rename(self, renaming) -> "Guard":
        return Guard([c.rename(renaming) for c in self.comparisons])

    def __str__(self):
        return " & ".join([str(c) for c in self.comparisons])

@dataclass
class Broadcast(Formula):
    variable: Variable
    guard: Guard
    port: Port
    index: int

    def rename(self, renaming):
        variable = self.variable.rename(renaming)
        guard = self.guard.rename(renaming)
        port = self.port.rename(renaming)
        return Broadcast(variable, guard, port, self.index)

    def __post_init__(self):
        if self.variable != self.port.variable:
            raise FormulaError(f"Broadcast variable mismatch")

    @property
    def free_variables(self) -> Set[Variable]:
        return self.guard.variables - {self.variable}

    @property
    def terms(self) -> List[Term]:
        terms = [self.variable]
        terms += self.guard.terms
        terms += self.port.terms
        return [t for i, t in enumerate(terms) if not t in terms[:i]]

    @property
    def local_terms(self) -> List[Term]:
        terms = self.terms
        return [t for t in terms if t.variable == self.variable]

    @property
    def contains_not_trivial_local_term(self) -> bool:
        result = any([not t.trivial_term for t in self.local_terms])
        return result

    def __str__(self):
        return f"all {self.variable}: {self.guard}. {self.port}"

@dataclass
class Clause(Formula):
    variables: List[Variable]
    guard: Guard
    ports: List[Port]
    broadcasts: List[Broadcast]
    index: int

    def _check_for_unknowns(self) -> None:
        used_variables = set()
        for p in self.ports:
            used_variables |= p.variables
        for b in self.broadcasts:
            used_variables |= b.free_variables
        used_variables |= self.guard.variables
        unknowns = {g for g in used_variables if not g in self.variables}
        if unknowns:
            raise FormulaError(f"{unknowns} are not quantified but used")

    def _check_for_unnecessary_quantification(self) -> None:
        used_variables = set()
        for p in self.ports:
            used_variables |= p.variables
        unneeded = {g for g in self.variables if g not in used_variables}
        if unneeded:
            raise FormulaError(f"{unneeded} are quantified but not used")

    def __post_init__(self):
        self._check_for_unknowns()
        self._check_for_unnecessary_quantification()
        unique_var_list = [v for i, v in enumerate(self.variables)
                if not v in self.variables[:i]]
        renaming = {v.name: f"x{i}" for i, v in enumerate(unique_var_list)}
        self.variables = [v.rename(renaming) for v in unique_var_list]
        self.guard = self.guard.rename(renaming)
        self.ports = [p.rename(renaming) for p in self.ports]
        broadcasts = []
        for i, b in enumerate(self.broadcasts):
            renaming[b.variable.name] = f"x{len(self.variables) + i}"
            broadcasts.append(b.rename(renaming))
        self.broadcasts = broadcasts

    @property
    def terms_in_guard(self) -> List[Term]:
        ret = list(self.variables)
        ret += self.guard.terms
        for p in self.ports:
            ret += p.terms
        return [t for i, t in enumerate(ret) if t not in ret[:i]]

    @property
    def contains_not_trivial_existential_term(self) -> bool:
        return any([not t.trivial_term for t in self.existential_terms])

    @property
    def terms(self) -> List[Term]:
        ret = self.terms_in_guard
        for b in self.broadcasts:
            ret += b.terms
        return [t for i, t in enumerate(ret) if t not in ret[:i]]

    @property
    def existential_terms(self) -> List[Term]:
        return [t for t in self.terms if t.variable in self.variables]

    @property
    def all_ports(self) -> List[Port]:
        all_ports = self.ports
        for b in self.broadcasts:
            all_ports += [b.port]
        return [p for i, p in enumerate(all_ports) if not p in all_ports[:i]]

    @property
    def broadcast_terms(self) -> List[Term]:
        return [t for t in self.terms if t not in self.terms_in_guard]

    def __str__(self):
        variables = ", ".join([str(v) for v in self.variables])
        guard = f" {self.guard}."
        ports = " & ".join([str(p) for p in self.ports])
        if self.broadcasts:
            broadcasts = " with " + " & ".join([str(b) for b in self.broadcasts])
        else:
            broadcasts = ""
        return f"{variables}:{guard} {ports}{broadcasts}"

@dataclass
class Interaction(Formula):
    clauses: List[Clause]

    @property
    def ports(self) -> List[Port]:
        ports = []
        for c in self.clauses:
            ports += c.ports
        return [p for i, p in enumerate(ports) if not p in ports[:i]]

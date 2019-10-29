from dataclasses import dataclass, field
from typing import List, Iterable, Set, Dict, Optional

class FormulaError(Exception):
    pass

class Formula(object):
    def __repr__(self):
        return f"{type(self)}<{str(self)}>"

    def __repr__(self) -> str:
        return f"{type(self)}<{self}>"

    @property
    def variables(self) -> Set["Variable"]:
        return set()

    @property
    def sorted_variables(self) -> List["Variable"]:
        return sorted(self.variables, key=str)

    def rename(self, renaming : Dict[str, str]) -> "Term":
        raise NotImplemented

    @property
    def all_terms(self) -> Set["Term"]:
        return set()

    @property
    def sorted_terms(self) -> List["Term"]:
        return sorted(self.all_terms, key=str)

    @property
    def variable_terms(self) -> List["Term"]:
        return [term for term in self.sorted_terms if not term.is_constant]

    @property
    def complex_terms(self) -> List["Term"]:
        return [term for term in self.sorted_terms if not term.is_atomic]

    @property
    def involved_variables(self) -> List["Term"]:
        return [term for term in self.sorted_terms
                if term.is_atomic and not term.is_constant]

class Term(Formula):
    @property
    def all_terms(self) -> Set["Term"]:
        return {self} | self.sub_terms

    @property
    def sub_terms(self) -> Set["Term"]:
        return set()

    @property
    def is_constant(self) -> bool:
        return False

    @property
    def is_atomic(self) -> bool:
        return self.is_constant


@dataclass
class Constant(Term):
    value: str

    def rename(self, renaming) -> "Constant":
        return Constant(self.value)

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value

    def __str__(self):
        return str(self.value)

    @property
    def is_constant(self) -> bool:
        return True

@dataclass
class Variable(Term):
    name: str

    @property
    def variables(self) -> Set["Variable"]:
        return {self}

    def rename(self, renaming):
        return Variable(renaming.get(self.name, self.name))

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __str__(self):
        return self.name

    @property
    def is_atomic(self) -> bool:
        return True

@dataclass
class Successor(Term):
    index: int # in {0, 1}
    argument: Term

    def __hash__(self):
        return hash(self.index) & hash(self.argument)

    def __eq__(self, other):
        return type(self) == type(other) and (
                self.argument == other.argument
                and self.index == other.index)

    @property
    def variables(self) -> Set[Variable]:
        return self.argument.variables

    def rename(self, renaming : Dict[str, str]) -> "Successor":
        return Successor(self.index, self.argument.rename(renaming))

    @property
    def sub_terms(self) -> Set[Term]:
        return self.argument.all_terms

    def __str__(self) -> str:
        return f"succ{self.index}({self.argument})"

@dataclass
class Predicate(Formula):
    name: str
    argument: Term

    def __hash__(self):
        return hash(self.name) & hash(self.argument)

    def __eq__(self, other):
        return type(self) == type(other) and (
                self.name == other.name and self.argument == other.argument)

    @property
    def variables(self) -> Set[Variable]:
        return self.argument.variables

    @property
    def all_terms(self) -> Set[Term]:
        return self.argument.all_terms

    def rename(self, renaming):
        return Predicate(self.name, self.argument.rename(renaming))

    def __str__(self):
        return f"{self.name}({self.argument})"

@dataclass
class PredicateCollection(Formula):
    predicates: Set[Predicate]

    @property
    def variables(self) -> Set[Variable]:
        from functools import reduce
        return set(reduce(
            lambda acc, p: p.variables | acc,
            self.predicates,
            set()))

    @property
    def all_terms(self) -> Set[Term]:
        from functools import reduce
        return set(reduce(
            lambda acc, p: p.all_terms | acc,
            self.predicates,
            set()))

    def rename(self, renaming: Dict[str, str]) -> "PredicateCollection":
        return type(self)({p.rename(renaming) for p in self.predicates})

    def __str__(self) -> str:
        return f" {self.comparison_symbol} ".join([str(p) for
            p in self.predicates])

@dataclass
class PredicateConjunction(PredicateCollection):
    @property
    def comparison_symbol(self) -> str:
        return "&"

@dataclass
class PredicateDisjunction(PredicateCollection):
    @property
    def comparison_symbol(self) -> str:
        return "|"

@dataclass
class Restriction(Formula):
    pass

@dataclass
class Last(Restriction):
    index: int
    argument: Term

    @property
    def variables(self) -> Set[Variable]:
        return self.argument.variables

    @property
    def all_terms(self) -> Set[Term]:
        return self.argument.all_terms

    def rename(self, renaming: Dict[str, str]) -> "Last":
        return Last(self.index, self.argument.rename(renaming))

    def __str__(self):
        return f"last{self.index}({self.argument})"

@dataclass
class Comparison(Restriction):
    left: Term
    right: Term

    @property
    def variables(self) -> Set[Variable]:
        return self.left.variables | self.right.variables

    @property
    def all_terms(self) -> Set[Term]:
        return self.left.all_terms | self.right.all_terms

    def rename(self, renaming: Dict[str, str]) -> "Comparison":
        return type(self)(self.left.rename(renaming),
                self.right.rename(renaming))

    def __str__(self):
        return f"{self.left} {self.comp_str} {self.right}"

@dataclass
class Below(Comparison):
    @property
    def comp_str(self):
        return "<"

@dataclass
class BelowEqual(Comparison):
    @property
    def comp_str(self):
        return "<="

@dataclass
class Above(Comparison):
    @property
    def comp_str(self):
        return ">"

@dataclass
class AboveEqual(Comparison):
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

@dataclass
class RestrictionCollection(Restriction):
    restrictions: List[Restriction]

    @property
    def variables(self) -> Set[Variable]:
        from functools import reduce
        return set(reduce(
            lambda acc, r: r.variables | acc,
            self.restrictions,
            set()))

    @property
    def all_terms(self) -> Set[Term]:
        from functools import reduce
        return set(reduce(
            lambda acc, r: r.all_terms | acc,
            self.restrictions,
            set()))

    def rename(self, renaming) -> "RestrictionCollection":
        return type(self)([r.rename(renaming) for r in self.restrictions])

    def __str__(self) -> str:
        restrictions = f" {self.comparison_symbol} ".join(
                [str(r) for r in self.restrictions])
        return f"( {restrictions} )"

@dataclass
class RestrictionConjunction(RestrictionCollection):
    @property
    def comparison_symbol(self) -> str:
        return "&"

@dataclass
class RestrictionDisjunction(RestrictionCollection):
    @property
    def comparison_symbol(self) -> str:
        return "|"

@dataclass
class Broadcast(Formula):
    variable: Variable
    guard: RestrictionDisjunction
    body: PredicateDisjunction

    def rename(self, renaming: Dict[str, str]) -> "Broadcast":
        variable = self.variable.rename(renaming)
        guard = self.guard.rename(renaming)
        body = self.body.rename(renaming)
        return Broadcast(variable, guard, body)

    def __post_init__(self):
        for predicate in self.body.predicates:
            if [self.variable] != predicate.involved_variables:
                raise FormulaError(f"Broadcast variable mismatch")

    @property
    def free_variables(self) -> Set[Variable]:
        return self.guard.variables - {self.variable}

    @property
    def variables(self) -> Set[Variable]:
        return self.guard.variables | {self.variable}

    @property
    def all_terms(self) -> Set[Term]:
        terms = {self.variable}
        terms |= self.guard.all_terms
        terms |= self.body.all_terms
        return terms

    @property
    def local_terms(self) -> List[Term]:
        return [t for t in all_terms if t.variable == self.variable]

    def __str__(self):
        return "broadcasting {{ {variable}: {guard}. {body} }}".format(
                variable=self.variable, guard=self.guard, body=self.body)

@dataclass
class Clause(Formula):
    guard: RestrictionConjunction
    ports: PredicateConjunction
    broadcasts: List[Broadcast]

    @property
    def free_variables(self) -> Set[Variable]:
        free_local_variables = self.ports.variables | self.guard.variables
        broadcast_variables = set()
        for b in self.broadcasts:
            broadcast_variables |= b.free_variables
        return free_local_variables | broadcast_variables

    @property
    def sorted_free_variables(self) -> List[Variable]:
        return [t for t in self.sorted_terms if t in self.free_variables]

    @property
    def variables(self) -> Set[Variable]:
        local_variables = self.ports.variables | self.guard.variables
        broadcast_variables = set()
        for b in self.broadcasts:
            broadcast_variables |= b.variables
        return local_variables | broadcast_variables

    def __post_init__(self):
        # renaming process
        renaming = {v.name: f"x{i}" for i, v in enumerate(self.free_variables)}
        self.guard = self.guard.rename(renaming)
        self.ports = self.ports.rename(renaming)
        broadcasts = []
        for i, b in enumerate(self.broadcasts):
            renaming[b.variable.name] = f"x{len(self.variables) + i}"
            broadcasts.append(b.rename(renaming))
        self.broadcasts = broadcasts

    @property
    def all_terms(self) -> Set[Term]:
        terms = self.guard.all_terms | self.ports.all_terms
        for b in self.broadcasts:
            terms |= b.all_terms
        return terms

    @property
    def free_terms(self) -> List[Term]:
        return [t for t in self.sorted_terms
                if t.variables.issubset(self.free_variables) and t.variables]

    @property
    def complex_constant_terms(self) -> List[Term]:
        res = [t for t in self.complex_terms
                if not t.is_constant and not t.variables]
        print(res)
        return res

    def __str__(self):
        return f"Clause({self.guard}, {self.ports}, {self.broadcasts})"

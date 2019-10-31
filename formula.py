from dataclasses import dataclass, field
from typing import List, Iterable, Set, Dict, Optional

class FormulaError(Exception):
    pass

class FormulaBase(object):
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
    def complex_terms(self) -> List["Term"]:
        return [term for term in self.sorted_terms if not term.is_atomic]

    @property
    def involved_variables(self) -> List["Term"]:
        return [term for term in self.sorted_terms
                if term.is_atomic and not term.is_constant]

class Formula(FormulaBase):
    pass

class Term(FormulaBase):
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
    value: int

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
    argument: Term

    def __hash__(self):
        return hash(self.argument)

    def __eq__(self, other):
        return type(self) == type(other) and (
                self.argument == other.argument)

    @property
    def variables(self) -> Set[Variable]:
        return self.argument.variables

    def rename(self, renaming : Dict[str, str]) -> "Successor":
        return Successor(self.argument.rename(renaming))

    @property
    def sub_terms(self) -> Set[Term]:
        return self.argument.all_terms

    def __str__(self) -> str:
        return f"succ({self.argument})"

@dataclass
class Predicate(Formula):
    name: str
    argument: Term

    def __post_init__(self):
        self._pre = None
        self._post = None

    @property
    def pre(self):
        if not self._pre:
            raise FormulaError("Unbound predicate does not have a preset")
        return self._pre

    @property
    def post(self):
        if not self._post:
            raise FormulaError("Unbound predicate does not have a postset")
        return self._post

    def bind(self, pre, post):
        if self._pre or self._post:
            raise FormulaError(f"Cannot re-bind predicate {self}")
        self._pre = pre
        self._post = post

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
        new_pred = Predicate(self.name, self.argument.rename(renaming))
        new_pred.bind(self._pre, self._post)
        return new_pred

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
    argument: Term

    @property
    def variables(self) -> Set[Variable]:
        return self.argument.variables

    @property
    def all_terms(self) -> Set[Term]:
        return self.argument.all_terms

    def rename(self, renaming: Dict[str, str]) -> "Last":
        return Last(self.argument.rename(renaming))

    def __str__(self):
        return f"last({self.argument})"

@dataclass
class Comparison(Restriction):
    left: Term
    right: Term

    def __eq__(self, other):
        return type(self) == type(other) and (
                self.left == other.left
                and self.right == other.right)

    @property
    def variables(self) -> Set[Variable]:
        return self.left.variables | self.right.variables

    @property
    def all_terms(self) -> Set[Term]:
        return self.left.all_terms | self.right.all_terms

    def rename(self, renaming: Dict[str, str]) -> "Comparison":
        return type(self)(self.left.rename(renaming),
                self.right.rename(renaming))

    def __str__(self) -> str:
        return f"{self.left} {self.comp_str} {self.right}"

@dataclass
class Less(Comparison):
    @property
    def comp_str(self):
        return "<"

@dataclass
class LessEqual(Comparison):
    @property
    def comp_str(self):
        return "<="

@dataclass
class Greater(Comparison):
    @property
    def comp_str(self):
        return ">"

@dataclass
class GreaterEqual(Comparison):
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
        # setup caching
        self._free_variables = None
        self._variables = None
        self._all_terms = None
        self._local_terms = None
        for predicate in self.body.predicates:
            if [self.variable] != predicate.involved_variables:
                raise FormulaError(f"Broadcast variable mismatch")

    @property
    def local_variables(self) -> List[Variable]:
        return [self.variable]

    @property
    def free_variables(self) -> Set[Variable]:
        if self._free_variables: return self._free_variables
        self._free_variables = self.guard.variables - {self.variable}
        return self._free_variables

    @property
    def variables(self) -> Set[Variable]:
        if self._variables: return self._variables
        self._variables = self.guard.variables | {self.variable}
        return self._variables

    @property
    def all_terms(self) -> Set[Term]:
        if self._all_terms: return self._all_terms
        terms = {self.variable}
        terms |= self.guard.all_terms
        terms |= self.body.all_terms
        self._all_terms = terms
        return self._all_terms

    @property
    def local_terms(self) -> List[Term]:
        if self._local_terms: return self._local_terms
        self._local_terms = [t for t in self.sorted_terms
                if t.variables.issubset({self.variable}) and t.variables]
        return self._local_terms

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
    def local_variables(self) -> List[Variable]:
        return self.sorted_free_variables

    @property
    def predicates(self) -> Set[Predicate]:
        predicates = set()
        predicates |= self.ports.predicates
        for b in self.broadcasts:
            predicates |= b.body.predicates
        return predicates

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
            renaming[b.variable.name] = f"x{len(self.free_variables) + i}"
            broadcasts.append(b.rename(renaming))
        self.broadcasts = broadcasts
        # adding disequality constraint for free variables to broadcasts
        for b in self.broadcasts:
            for conjunct in b.guard.restrictions:
                var = b.variable
                disequalities = [Unequal(var, v)
                            for v in self.free_variables
                            if (not Unequal(var, v) in conjunct.restrictions
                                or Unequal(v, var) in conjunct.restrictions)]
                conjunct.restrictions += disequalities

    @property
    def all_terms(self) -> Set[Term]:
        terms = self.guard.all_terms | self.ports.all_terms
        for b in self.broadcasts:
            terms |= b.all_terms
        return terms

    @property
    def local_terms(self) -> List[Term]:
        return [t for t in self.sorted_terms
                if t.variables.issubset(self.free_variables)]

    def __str__(self):
        return f"Clause({self.guard}, {self.ports}, {self.broadcasts})"

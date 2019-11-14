from dataclasses import dataclass

from typing import List, Set, Dict, cast

from system import System


class FormulaError(Exception):
    pass


@dataclass
class FormulaBase:
    system: System

    def __repr__(self):
        return f"{type(self)}<{str(self)}>"

    def __post_init__(self):
        self.variables: Set["Variable"] = set()
        self.sorted_variables: List["Variable"] = sorted(self.variables,
                                                         key=str)
        self.all_terms: Set["Term"] = set()

    @property
    def sorted_terms(self) -> List["Term"]:
        return sorted(self.all_terms, key=str)

    @property
    def complex_terms(self) -> List["Term"]:
        return [term for term in self.sorted_terms
                if (type(term) is not Constant
                    or type(term) is not Variable)]

    @property
    def involved_variables(self) -> List["Variable"]:
        involved_variables = []
        for term in self.sorted_terms:
            if type(term) is Variable:
                term = cast(Variable, term)
                involved_variables.append(term)
        return involved_variables

    def rename(self, renaming: Dict[str, str]) -> "FormulaBase":
        raise NotImplementedError()


class Formula(FormulaBase):
    pass


@dataclass
class Term(FormulaBase):
    def __post_init__(self):
        super().__post_init__()
        self.sub_terms: Set["Term"] = set()
        self.all_terms: Set["Term"] = {self}

    def rename(self, rename: Dict[str, str]) -> "Term":
        raise NotImplementedError()


@dataclass
class Constant(Term):
    value: int

    def __post_init__(self):
        super().__post_init__()
        self.all_terms: Set["Term"] = {self}

    def rename(self, renaming) -> "Constant":
        return Constant(self.value)

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value

    def __str__(self):
        return str(self.value)


@dataclass
class Variable(Term):
    name: str

    def __post_init__(self):
        super().__post_init__()
        self.all_terms: Set["Term"] = {self}
        self.variables: Set["Variable"] = {self}

    def rename(self, renaming: Dict[str, str]) -> "Variable":
        return Variable(renaming.get(self.name, self.name))

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __str__(self):
        return self.name


@dataclass
class Successor(Term):
    argument: Term

    def __post_init__(self):
        super().__post_init__()
        self.sub_terms: Set["Term"] = self.arguemnt.all_terms
        self.variables: Set["Variable"] = self.argument.variables

    def __hash__(self):
        return hash("succ") & hash(self.argument)

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.argument == other.argument)

    def rename(self, renaming: Dict[str, str]) -> "Successor":
        return Successor(self.argument.rename(renaming))

    def __str__(self) -> str:
        return f"succ({self.argument})"


@dataclass
class Predicate(Formula):
    name: str
    argument: Term
    pre: str
    post: str

    def __post_init__(self):
        super().__post_init__()
        self.variables: Set[Variable] = self.argument.variables
        self.all_terms: Set[Term] = self.argument.all_terms

    def __hash__(self):
        return hash(self.name) & hash(self.argument)

    def __eq__(self, other):
        return (type(self) == type(other)
                and self.name == other.name
                and self.argument == other.argument)

    def rename(self, renaming: Dict[str, str]) -> "Predicate":
        new_pred = Predicate(self.name, self.argument.rename(renaming))
        new_pred.bind(self._pre, self._post)
        return new_pred

    def __str__(self):
        return f"{self.name}({self.argument})"


@dataclass
class PredicateCollection(Formula):
    predicates: Set[Predicate]

    def __post_init__(self):
        super().__post_init__()
        self.variables: Set[Variable] = set()
        self.all_terms: Set[Term] = set()
        self.comparison_symbol: str = ""
        for p in self.predicates:
            self.variables |= p.variables
            self.all_terms |= p.all_terms

    def rename(self, renaming: Dict[str, str]) -> "PredicateCollection":
        return type(self)({p.rename(renaming) for p in self.predicates})

    def __str__(self) -> str:
        return f" {self.comparison_symbol} ".join([str(p) for
                                                   p in self.predicates])


@dataclass
class PredicateConjunction(PredicateCollection):
    def __post_init__(self):
        super().__post_init__()
        self.comparison_symbol: str = "&"

    def rename(self, renaming: Dict[str, str]) -> "PredicateConjunction":
        return cast("PredicateConjunction", super().rename(renaming))


@dataclass
class PredicateDisjunction(PredicateCollection):
    def __post_init__(self):
        super().__post_init__()
        self.comparison_symbol: str = "|"

    def rename(self, renaming: Dict[str, str]) -> "PredicateDisjunction":
        return cast("PredicateDisjunction", super().rename(renaming))


@dataclass
class Restriction(Formula):
    def rename(self, renaming: Dict[str, str]) -> "Restriction":
        raise NotImplementedError()


@dataclass
class Last(Restriction):
    argument: Term

    def __hash__(self):
        return hash("last") & hash(self.argument)

    def __eq__(self, other):
        return type(self) is type(other) and self.argument == other.argument

    def __post_init__(self):
        super().__post_init__()
        self.variables: Set[Variable] = self.argument.variables
        self.all_terms: Set[Term] = self.argument.all_terms

    def rename(self, renaming: Dict[str, str]) -> "Last":
        return Last(self.argument.rename(renaming))

    def __str__(self):
        return f"last({self.argument})"


@dataclass
class Comparison(Restriction):
    left: Term
    right: Term

    def __post_init__(self):
        super().__post_init__()
        self.comp_str: str = ""
        self.variables: Set[Variable] = (self.left.variables
                                         | self.right.variables)
        self.all_terms: Set[Term] = (self.left.all_terms
                                     | self.right.all_terms)

    def rename(self, renaming: Dict[str, str]) -> "Comparison":
        return type(self)(self.left.rename(renaming),
                          self.right.rename(renaming))

    def __str__(self) -> str:
        return f"{self.left} {self.comp_str} {self.right}"

    def __hash__(self):
        return hash(self.left) & hash(self.right)

    def __eq__(self, other) -> bool:
        return (type(self) is type(other)
                and self.left == other.left
                and self.right == other.right)


@dataclass
class Less(Comparison):
    def __post_init__(self):
        super().__post_init__()
        self.comp_str: str = "<"


@dataclass
class LessEqual(Comparison):
    def __post_init__(self):
        super().__post_init__()
        self.comp_str: str = "<="


@dataclass
class Equal(Comparison):
    def __post_init__(self):
        super().__post_init__()
        self.comp_str: str = "="

    def __eq__(self, other) -> bool:
        return (type(self) is type(other)
                and ((self.left == other.left
                      and self.right == other.right)
                     or (self.left == other.right
                         and self.right == other.left)))


@dataclass
class Unequal(Comparison):
    def __post_init__(self):
        super().__post_init__()
        self.comp_str: str = "~="

    def __eq__(self, other) -> bool:
        return (type(self) is type(other)
                and ((self.left == other.left
                      and self.right == other.right)
                     or (self.left == other.right
                         and self.right == other.left)))


@dataclass
class RestrictionCollection(Restriction):
    restrictions: Set[Restriction]

    def __post_init__(self):
        super().__post_init__()
        self.variables: Set[Variable] = set()
        self.all_terms: Set[Term] = set()
        self.comparison_symbol: str = ""
        for r in self.restrictions:
            self.variables |= r.variables
            self.all_terms |= r.all_terms

    def rename(self, renaming) -> "RestrictionCollection":
        return type(self)({r.rename(renaming) for r in self.restrictions})

    def __str__(self) -> str:
        restrictions = f" {self.comparison_symbol} ".join(
                [str(r) for r in self.restrictions])
        return f"( {restrictions} )"


@dataclass
class RestrictionConjunction(RestrictionCollection):
    def __post_init__(self):
        self.comparison_symbol: str = "&"

    def rename(self, renaming) -> "RestrictionConjunction":
        return cast("RestrictionConjunction", super().rename(renaming))


@dataclass
class RestrictionDisjunction(RestrictionCollection):
    def __post_init__(self):
        self.comparison_symbol: str = "|"

    def rename(self, renaming) -> "RestrictionDisjunction":
        return cast("RestrictionDisjunction", super().rename(renaming))


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
        super().__post_init__()
        self.local_variables: List[Variable] = [self.variable]
        self.free_variables: Set[Variable] = (self.guard.variables
                                              - {self.variable})
        self.variables: Set[Variable] = self.guard.variables | {self.variable}
        self.all_terms: Set[Term] = ({self.variable}
                                     | self.guard.all_terms
                                     | self.body.all_terms)
        self.local_terms: Set[Term] = {t for t in self.sorted_terms
                                       if t.variables == {self.variable}}
        if any([[self.variable] != predicate.involved_variables
                for predicate in self.body.predicate]):
            raise FormulaError(f"Broadcast variable mismatch")

    def __str__(self):
        return "broadcasting {{ {variable}: {guard}. {body} }}".format(
                variable=self.variable, guard=self.guard, body=self.body)


@dataclass
class Clause(Formula):
    guard: RestrictionConjunction
    ports: PredicateConjunction
    broadcasts: List[Broadcast]

    # def normalize(self) -> "Clause":
    #     # renaming process
    #     renaming = {v.name: f"x{i}" for i, v in enumerate(self.free_variables)}
    #     new_guard = self.guard.rename(renaming)
    #     new_ports = self.ports.rename(renaming)
    #     broadcasts = []
    #     for i, b in enumerate(self.broadcasts):
    #         renaming[b.variable.name] = f"x{len(self.free_variables) + i}"
    #         broadcasts.append(b.rename(renaming))
    #     self.broadcasts = broadcasts
    #     # adding disequality constraint for free variables to broadcasts
    #     for b in self.broadcasts:
    #         for conjunct in b.guard.restrictions:
    #             var = b.variable
    #             disequalities = [Unequal(var, v)
    #                              for v in self.free_variables
    #                              if not
    #                              (Unequal(var, v) in conjunct.restrictions
    #                               or Unequal(v, var) in
# conjunct.restrictions)]
    #             conjunct.restrictions += disequalities

    def __post_init__(self):
        super().__post_init__()
        self.variables: Set[Variable] = (self.ports.variables
                                         | self.guard.variables)
        self.free_variables: Set[Variable] = (self.ports.variables
                                              | self.guard.variables)
        self.predicates: Set[Predicate] = self.ports.predicates
        self.all_terms: Set[Term] = self.guard.all_terms | self.ports.all_terms
        for b in self.broadcasts:
            self.variables |= b.variables
            self.free_variables |= b.free_variables
            self.predicates |= b.body.predicates
            self.all_terms |= b.all_terms
        self.sorted_free_variables = [t for t in self.sorted_terms
                                      if t in self.free_variables]
        self.local_variables = self.sorted_free_variables
        self.local_terms: Set[Term] = {t for t in self.sorted_terms
                                       if t.variables.issubset(
                                           self.free_variables)}

    def __str__(self):
        return f"Clause({self.guard}, {self.ports}, {self.broadcasts})"


@dataclass
class Interaction:
    clauses: List[Clause]
    system: System
    assumptions: Dict[str, str]
    properties: Dict[str, str]

    @property
    def property_names(self) -> List[str]:
        return sorted(list(self.properties.keys()) + ["deadlock"])

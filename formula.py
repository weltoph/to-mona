from dataclasses import dataclass, field

from typing import List, Set, Dict, cast, Tuple, FrozenSet

from system import System

import logging

import mona

logger = logging.getLogger(__name__)


class FormulaError(Exception):
    pass


@dataclass(frozen=True)
class FormulaBase:
    system: System = field(repr=False)

    def __repr__(self):
        return f"{type(self)}<{str(self)}>"

    def __post_init__(self):
        variables: Set["Variable"] = set()
        all_terms: Set["Term"] = set()
        object.__setattr__(self, 'variables', variables)
        object.__setattr__(self, 'all_terms', all_terms)

    def substitute(self,
                   substitution: Dict["Term", "Variable"]) -> "FormulaBase":
        raise NotImplementedError()


class Formula(FormulaBase):
    pass


@dataclass(frozen=True)
class Term(FormulaBase):
    def __post_init__(self):
        super().__post_init__()
        all_terms: Set["Term"] = {self}
        object.__setattr__(self, 'all_terms', all_terms)

    def substitute(self, substitution: Dict["Term", "Variable"]) -> "Variable":
        raise NotImplementedError()

    def term_normalization(self,
                           variable_substitution: Dict["Term", "Variable"]
                           ) -> Tuple[Set["Restriction"], "Variable"]:
        raise NotImplementedError()

    def __lt__(self, other: "Term") -> bool:
        return str(self) < str(other)


@dataclass(frozen=True)
class Constant(Term):
    value: int

    def substitute(self, substitution: Dict["Term", "Variable"]) -> "Variable":
        try:
            return substitution[self]
        except KeyError:
            raise FormulaError(f"{substitution} does not account for {self}")

    def term_normalization(self,
                           variable_substitution: Dict["Term", "Variable"]
                           ) -> Tuple[Set["Restriction"], "Variable"]:
        r_var = Variable(self.system, f"c_{self.value}")
        restriction = Equal(self.system,
                            r_var, Constant(self.system, self.value))
        return ({restriction}, r_var)

    def __str__(self):
        return str(self.value)


@dataclass(frozen=True)
class Variable(Term):
    name: str

    def __post_init__(self):
        super().__post_init__()
        variables: Set["Variable"] = {self}
        object.__setattr__(self, 'variables', variables)

    def substitute(self, substitution: Dict["Term", "Variable"]) -> "Variable":
        equiv_var = Variable(self.system, self.name)
        return substitution.get(self, equiv_var)

    def term_normalization(self,
                           variable_substitution: Dict["Term", "Variable"]
                           ) -> Tuple[Set["Restriction"], "Variable"]:
        try:
            r_var = variable_substitution[self]
        except KeyError:
            raise FormulaError(f"{variable_substitution} does not account for",
                               f" {self}")
        return (set(), r_var)

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class Successor(Term):
    argument: Term

    def __post_init__(self):
        super().__post_init__()
        variables: Set["Variable"] = self.argument.variables
        object.__setattr__(self, 'variables', variables)

    def term_normalization(self,
                           variable_substitution: Dict["Term", "Variable"]
                           ) -> Tuple[Set["Restriction"], "Variable"]:
        restrictions, argument = self.argument.term_normalization(
                variable_substitution)
        new_variable = Variable(self.system, f"succ_{argument.name}")
        new_restriction = IsNext(self.system, argument, new_variable)
        return (restrictions | {new_restriction}, new_variable)

    def substitute(self, substitution: Dict["Term", "Variable"]) -> "Variable":
        try:
            return substitution[self]
        except KeyError:
            raise FormulaError(f"{substitution} does not account for {self}")

    def __str__(self) -> str:
        return f"succ({self.argument})"


@dataclass(frozen=True)
class Predicate(Formula):
    name: str
    argument: Term
    pre: str
    post: str

    def __post_init__(self):
        super().__post_init__()
        variables: Set[Variable] = self.argument.variables
        all_terms: Set[Term] = self.argument.all_terms
        object.__setattr__(self, 'variables', variables)
        object.__setattr__(self, 'all_terms', all_terms)

    def substitute(self,
                   substitution: Dict["Term", "Variable"]) -> "Predicate":
        new_pred = Predicate(self.system, self.name,
                             self.argument.substitute(substitution),
                             self.pre, self.post)
        return new_pred

    def __str__(self):
        return f"{self.name}({self.argument})"


@dataclass(frozen=True)
class PredicateCollection(Formula):
    predicates: FrozenSet[Predicate]

    def __post_init__(self):
        super().__post_init__()
        variables: Set[Variable] = set()
        all_terms: Set[Term] = set()
        for p in self.predicates:
            variables |= p.variables
            all_terms |= p.all_terms
        object.__setattr__(self, 'variables', variables)
        object.__setattr__(self, 'all_terms', all_terms)

    def substitute(self,
                   substitution: Dict["Term",
                                      "Variable"]) -> "PredicateCollection":
        return type(self)(self.system,
                          frozenset({p.substitute(substitution)
                                     for p in self.predicates}))


@dataclass(frozen=True)
class PredicateConjunction(PredicateCollection):
    def __post_init__(self):
        super().__post_init__()

    def substitute(self,
                   substitution: Dict["Term",
                                      "Variable"]) -> "PredicateConjunction":
        return cast("PredicateConjunction", super().substitute(substitution))

    def __str__(self) -> str:
        return f" & ".join([str(p) for  # type: ignore attr-defined # noqa: E501, F723
                            p in self.predicates])


@dataclass(frozen=True)
class PredicateDisjunction(PredicateCollection):
    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, 'comparision_symbol', "|")

    def substitute(self,
                   substitution: Dict["Term",
                                      "Variable"]) -> "PredicateDisjunction":
        return cast("PredicateDisjunction", super().substitute(substitution))

    def __str__(self) -> str:
        return f" | ".join([str(p) for  # type: ignore attr-defined # noqa: E501, F723
                            p in self.predicates])


@dataclass(frozen=True)
class Restriction(Formula):
    def substitute(self,
                   substitution: Dict["Term", "Variable"]) -> "Restriction":
        raise NotImplementedError()


@dataclass(frozen=True)
class Last(Restriction):
    argument: Term

    def __post_init__(self):
        super().__post_init__()
        variables: Set[Variable] = self.argument.variables
        all_terms: Set[Term] = self.argument.all_terms
        object.__setattr__(self, 'all_terms', all_terms)
        object.__setattr__(self, 'variables', variables)

    def substitute(self, substitution: Dict["Term", "Variable"]) -> "Last":
        return Last(self.system, self.argument.substitute(substitution))

    def __str__(self):
        return f"last({self.argument})"

    def as_mona(self):
        argument = self.argument.as_mona
        return mona.PredicateCall("is_last", argument)


@dataclass(frozen=True)
class Comparison(Restriction):
    left: Term
    right: Term

    def __post_init__(self):
        super().__post_init__()
        variables: Set[Variable] = (self.left.variables
                                    | self.right.variables)
        all_terms: Set[Term] = (self.left.all_terms
                                | self.right.all_terms)
        object.__setattr__(self, 'variables', variables)
        object.__setattr__(self, 'all_terms', all_terms)

    def substitute(self,
                   substitution: Dict["Term", "Variable"]) -> "Comparison":
        return type(self)(self.system, self.left.substitute(substitution),
                          self.right.substitute(substitution))

    def __str__(self) -> str:
        return f"{self.left} {self.comp_str} {self.right}"  # type: ignore attr-defined # noqa: E501, F723

    def __hash__(self):
        return hash(self.left) & hash(self.right)

    def __eq__(self, other) -> bool:
        return (type(self) is type(other)
                and self.left == other.left
                and self.right == other.right)


@dataclass(frozen=True)
class IsNext(Comparison):
    def __str__(self) -> str:
        return f"is_next({self.left}, {self.right})"

    def as_mona(self):
        left = self.left.as_mona()
        right = self.right.as_mona()
        return PredicateCall("is_next", [left, right])


@dataclass(frozen=True)
class Less(Comparison):
    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, 'comp_str', "<")

    def as_mona(self):
        left = self.left.as_mona()
        right = self.right.as_mona()
        return mona.Less(left, right)


@dataclass(frozen=True)
class LessEqual(Comparison):
    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, 'comp_str', "<=")

    def as_mona(self):
        left = self.left.as_mona()
        right = self.right.as_mona()
        return mona.LessEqual(left, right)


@dataclass(frozen=True)
class Equal(Comparison):
    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, 'comp_str', "=")

    def __eq__(self, other) -> bool:
        return (type(self) is type(other)
                and ((self.left == other.left
                      and self.right == other.right)
                     or (self.left == other.right
                         and self.right == other.left)))

    def __hash__(self):
        return hash(self.left) & hash(self.right)

    def as_mona(self):
        left = self.left.as_mona()
        right = self.right.as_mona()
        return mona.Equal(left, right)


@dataclass(frozen=True)
class Unequal(Comparison):
    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, 'comp_str', "~=")

    def __eq__(self, other) -> bool:
        return (type(self) is type(other)
                and ((self.left == other.left
                      and self.right == other.right)
                     or (self.left == other.right
                         and self.right == other.left)))

    def __hash__(self):
        return hash(self.left) & hash(self.right)

    def as_mona(self):
        left = self.left.as_mona()
        right = self.right.as_mona()
        return mona.Unequal(left, right)


@dataclass(frozen=True)
class RestrictionCollection(Restriction):
    restrictions: FrozenSet[Restriction]

    def __post_init__(self):
        super().__post_init__()
        variables: Set[Variable] = set()
        all_terms: Set[Term] = set()
        for r in self.restrictions:
            variables |= r.variables
            all_terms |= r.all_terms
        object.__setattr__(self, 'all_terms', all_terms)
        object.__setattr__(self, 'variables', variables)

    def substitute(self,
                   substitution: Dict["Term",
                                      "Variable"]) -> "RestrictionCollection":
        return RestrictionCollection(self.system,
                                     frozenset({r.substitute(substitution)
                                                for r in self.restrictions}))

    def __str__(self) -> str:
        restrictions = ", ".join([str(r) for r in self.restrictions])
        return f"( {restrictions} )"


@dataclass(frozen=True)
class Broadcast(Formula):
    variable: Variable
    guard: RestrictionCollection  # DNF
    body: PredicateDisjunction
    quantified_variables: Set[Variable] = field(default_factory=set)

    def guard_as_mona(self):
        return mona.Disjunction([
                mona.Conjunction([
                    f.as_mona() for f in c.restrictions])
                for c in self.guard.restrictions])

    def _substitute_elements(self, substitution: Dict["Term", "Variable"]
                             ) -> Tuple[Variable,
                                        RestrictionCollection,
                                        PredicateDisjunction,
                                        Set[Variable]]:
        variable = self.variable.substitute(substitution)
        quantified_variables = {variable.substitute(substitution)
                                for variable in self.quantified_variables}
        guard = self.guard.substitute(substitution)
        body = self.body.substitute(substitution)
        return (variable, guard, body, quantified_variables)

    def substitute(self,
                   substitution: Dict["Term", "Variable"]) -> "Broadcast":
        var, guard, body, q_vars = self._substitute_elements(substitution)
        return Broadcast(self.system, var, guard, body, q_vars)

    def normalize(self, substitutions: Dict["Term", "Variable"]
                  ) -> "Broadcast":
        logger.debug(f"normalizing broadcast {self}")
        local_terms = {t for t in self.all_terms  # type: ignore attr-defined # noqa: E501, F723
                       if (t.variables  # thus, no term on constant basis
                           and t.variables.issubset({self.variable}))}
        logger.debug(f"identifying local terms {local_terms}")
        logger.debug(f"going over local terms with {substitutions}")
        term_substitions = dict(substitutions)
        all_restrictions: Set[Restriction] = set()
        for term in local_terms:
            restrictions, variable = term.term_normalization(term_substitions)
            all_restrictions |= restrictions
            term_substitions[term] = variable
        logger.debug(f"gathered new restrictions {all_restrictions}"
                     + " and " + f" substitutions: {term_substitions}")
        var, guard, body, q_vars = self._substitute_elements(term_substitions)
        new_guard_clauses = set()
        for coll in guard.restrictions:
            coll = cast(RestrictionCollection, coll)
            new_guard_clauses.add(
                    cast(Restriction,
                         RestrictionCollection(self.system,
                                               (coll.restrictions
                                                | all_restrictions))))
        new_guard = RestrictionCollection(self.system,
                                          frozenset(new_guard_clauses))
        n_broadcast = Broadcast(self.system, var, new_guard, body, q_vars)
        logger.debug(f"Normalized\n\t{self}\nto\n\t{n_broadcast}")
        return n_broadcast

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, 'quantified_variables',
                           self.quantified_variables | {self.variable})
        free_variables: Set[Variable] = (self.guard.variables
                                         - self.quantified_variables)
        variables: Set[Variable] = (self.guard.variables
                                    | self.quantified_variables)
        all_terms: Set[Term] = (self.quantified_variables
                                | self.guard.all_terms
                                | self.body.all_terms)
        if any([not predicate.variables.issubset(self.quantified_variables)
                for predicate in self.body.predicates]):
            raise FormulaError(f"Broadcast variable mismatch")
        object.__setattr__(self, 'all_terms', all_terms)
        object.__setattr__(self, 'variables', variables)
        object.__setattr__(self, 'free_variables', free_variables)

    def __str__(self):
        return "broadcasting {{ {variables}: {guard}. {body} }}".format(
                variables=", ".join([str(v)
                                     for v in self.quantified_variables]),
                guard=self.guard,
                body=self.body)


@dataclass(frozen=True)
class Clause(Formula):
    guard: RestrictionCollection  # Conjunction of Atoms
    ports: PredicateConjunction
    broadcasts: List[Broadcast]

    def guard_as_mona(self):
        return mona.Conjunction([c.as_mona() for c in self.guard.restrictions])

    def __post_init__(self):
        super().__post_init__()
        variables: Set[Variable] = (self.ports.variables
                                    | self.guard.variables)
        free_variables: Set[Variable] = (self.ports.variables
                                         | self.guard.variables)
        predicates: Set[Predicate] = self.ports.predicates
        all_terms: Set[Term] = self.guard.all_terms | self.ports.all_terms
        for b in self.broadcasts:
            variables |= b.variables
            free_variables |= b.free_variables
            predicates |= b.body.predicates
            all_terms |= b.all_terms
        local_terms: Set[Term] = {t for t in self.all_terms
                                  if t.variables.issubset(
                                      self.free_variables)}
        object.__setattr__(self, 'all_terms', all_terms)
        object.__setattr__(self, 'variables', variables)
        object.__setattr__(self, 'predicates', predicates)
        object.__setattr__(self, 'free_variables', free_variables)
        object.__setattr__(self, 'local_terms', local_terms)

    def __str__(self) -> str:
        if res := self.guard.restrictions:  # noqa: E203, E701, E231
            guard = " & ".join([str(g) for g in sorted(res, key=str)])
        else:
            guard = "true"
        if preds := self.ports.predicates:  # noqa: E203, E701, E231
            ports = " & ".join([str(p) for p in sorted(preds, key=str)])
        else:
            ports = "true"
        broadcasts = "\n\t".join([str(b) for b in self.broadcasts])
        return f"{guard}. {ports} {broadcasts}"

    def normalize_terms(self) -> "Clause":
        local_constant_terms = {t for t in self.all_terms  # type: ignore attr-defined # noqa: E501, F723
                                if t.variables.issubset(self.free_variables)}  # type: ignore attr-defined # noqa: E501, F723
        sorted_vars = sorted([v for v in self.free_variables])  # type: ignore attr-defined # noqa: E501, F723
        renaming: Dict[Term, Variable] = {v: Variable(self.system, f"x_{i}")
                                          for i, v in enumerate(sorted_vars)}
        term_substitions = {}
        all_restrictions: Set[Restriction] = set()
        for term in local_constant_terms:
            restrictions, variable = term.term_normalization(renaming)
            all_restrictions |= restrictions
            term_substitions[term] = variable
        renaming.update(term_substitions)
        broadcasts = []
        for j, broadcast in enumerate(self.broadcasts):
            replacement_variable = Variable(self.system, f"b_{j}")
            renaming[broadcast.variable] = replacement_variable
            n_broadcast = broadcast.normalize(renaming)
            broadcasts.append(n_broadcast)
        new_guard = RestrictionCollection(
                self.system, self.guard.restrictions | all_restrictions)
        new_ports = self.ports.substitute(renaming)
        n_clause = Clause(self.system, new_guard, new_ports, broadcasts)
        logger.info(f"Normalized terms in\n\t{self}\nto\n\t{n_clause}")
        return n_clause

    def check_type_consistency(self) -> "Clause":
        free_types = {p.argument: self.system.components_of_labels[p.name]  # type: ignore attr-defined # noqa: E501, F723
                      for p in self.ports.predicates}
        broadcast_types = {j: {self.system.components_of_labels[p.name]  # type: ignore attr-defined # noqa: E501, F723
                               for p in b.body.predicates}
                           for j, b in enumerate(self.broadcasts)}
        for j in broadcast_types:
            if len(labels := broadcast_types[j]) != 1:  # noqa: E203, E231
                b = self.broadcasts[j]
                raise FormulaError(f"Inconsistent types in {b}")
            else:
                broadcast_types[j] = labels.pop()
        new_broadcasts: List[Broadcast] = []
        for j, bc in broadcast_types.items():
            broadcast = self.broadcasts[j]
            gathered_restrictions: Set[Restriction] = set()
            for v, fc in free_types.items():
                new_restrictions: Set[Restriction] = set()
                if fc != bc:
                    continue
                else:
                    potential_restrictions: Set[Restriction] = {
                            Unequal(self.system, v, o)
                            for o in broadcast.quantified_variables}
                    for conjunct in broadcast.guard.restrictions:
                        conjunct = cast(RestrictionCollection, conjunct)
                        if not potential_restrictions.issubset(
                                conjunct.restrictions):
                            new_restrictions = potential_restrictions
                            logger.warning(f"{broadcast} might shadow {v}")
                            logger.warning(f"adding {new_restrictions}")
                            break
                        else:
                            continue
                gathered_restrictions |= new_restrictions
            new_guards: Set[RestrictionCollection] = set()
            for restriction in broadcast.guard.restrictions:
                restriction = cast(RestrictionCollection, restriction)
                new_guards.add(RestrictionCollection(
                    self.system, frozenset(restriction.restrictions
                                           | gathered_restrictions)))
            new_guard = RestrictionCollection(self.system,
                                              frozenset(new_guards))
            new_broadcasts.append(Broadcast(self.system,
                                            broadcast.variable,
                                            new_guard,
                                            broadcast.body,
                                            broadcast.quantified_variables))
        n_clause = Clause(self.system, self.guard, self.ports, new_broadcasts)
        logger.info(f"Normalized\n\t{self}\nto\n\t{n_clause}")
        return n_clause

    def normalize(self) -> "Clause":
        n_clause = self.normalize_terms()
        n_clause = n_clause.check_type_consistency()
        return n_clause


@dataclass(frozen=True)
class Interaction:
    clauses: List[Clause]
    system: System
    assumptions: Dict[str, str]
    properties: Dict[str, str]

    @property
    def property_names(self) -> List[str]:
        return sorted(list(self.properties.keys()) + ["deadlock"])

    def normalize(self) -> "Interaction":
        return Interaction([c.normalize() for c in self.clauses],
                           self.system,
                           self.assumptions,
                           self.properties)

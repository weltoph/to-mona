from dataclasses import dataclass, field

from typing import List, Set, Dict, cast, Tuple, FrozenSet, Optional, Union

from system import System

import logging

import mona

import jinja2

logger = logging.getLogger(__name__)

env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('./')
    )


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

    def as_mona(self) -> mona.Term:
        raise NotImplementedError()

    def substitute(self, substitution: Dict["Term", "Variable"]
                   ) -> Union["Constant", "Variable"]:
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

    def substitute(self, substitution: Dict["Term", "Variable"]
                   ) -> Union["Variable", "Constant"]:
        try:
            return substitution[self]
        except KeyError:
            return Constant(self.system, self.value)

    def term_normalization(self,
                           variable_substitution: Dict["Term", "Variable"]
                           ) -> Tuple[Set["Restriction"], "Variable"]:
        r_var = Variable(self.system, f"c_{self.value}")
        restriction = Equal(self.system,
                            r_var, Constant(self.system, self.value))
        return ({restriction}, r_var)

    def __str__(self):
        return str(self.value)

    def as_mona(self):
        return mona.TermConstant(self.value)


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

    def as_mona(self):
        return mona.Variable(self.name)


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

    def hit_pre(self) -> mona.ElementIn:
        argument = self.argument.as_mona()
        if not type(argument) is mona.Variable:
            raise FormulaError(f"Predicate {self} is not normalized")
        argument = cast(mona.Variable, argument)
        return mona.ElementIn(
                argument,
                mona.Variable(self.pre))

    def hit_post(self) -> mona.ElementIn:
        argument = self.argument.as_mona()
        if not type(argument) is mona.Variable:
            raise FormulaError(f"Predicate {self} is not normalized")
        argument = cast(mona.Variable, argument)
        return mona.ElementIn(
                argument,
                mona.Variable(self.post))

    def miss_pre(self) -> mona.ElementNotIn:
        argument = self.argument.as_mona()
        if not type(argument) is mona.Variable:
            raise FormulaError(f"Predicate {self} is not normalized")
        argument = cast(mona.Variable, argument)
        return mona.ElementNotIn(
                argument,
                mona.Variable(self.pre))

    def miss_post(self) -> mona.ElementNotIn:
        argument = self.argument.as_mona()
        if not type(argument) is mona.Variable:
            raise FormulaError(f"Predicate {self} is not normalized")
        argument = cast(mona.Variable, argument)
        return mona.ElementNotIn(
                argument,
                mona.Variable(self.post))

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

    def as_mona(self) -> mona.Formula:
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
        argument = self.argument.as_mona()
        return mona.PredicateCall("is_last", [argument])


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
        return mona.PredicateCall("is_next", [left, right])


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

    def vertical_invariant(self) -> mona.Formula:
        substitution = {cast(Term, v): Variable(self.system,
                                                f"substitute_{v.name}")
                        for v in self.quantified_variables}
        try:
            renamed_broadcast = self.substitute(substitution)
        except FormulaError:
            raise FormulaError("Cannot generate formula for non-normalized"
                               + " Broadcast {self}")
        pos_variables = sorted([cast(mona.Variable, v.as_mona())
                                for v in self.quantified_variables], key=str)
        pos_guard = self.guard_as_mona()
        neg_variables = sorted([
            cast(mona.Variable, v.as_mona())
            for v in renamed_broadcast.quantified_variables], key=str)
        neg_guard = renamed_broadcast.guard_as_mona()
        others_empty = mona.UniversalFirstOrder(
            neg_variables,
            mona.Implication(
                mona.Conjunction([
                    neg_guard,
                    mona.Unequal(cast(mona.Variable,
                                      substitution[self.variable].as_mona()),
                                 cast(mona.Variable,
                                      self.variable.as_mona()))]),
                mona.Conjunction([cast(mona.Formula, p.miss_post())
                                  for p in renamed_broadcast.body.predicates]
                                 + [p.miss_pre()
                                    for p in renamed_broadcast.body.predicates]
                                 )))
        chosen_vertical = mona.Conjunction([
            mona.Conjunction([mona.Implication(p.hit_pre(), p.hit_post()),
                              mona.Implication(p.hit_post(), p.hit_pre())])
            for p in self.body.predicates])
        outer = mona.ExistentialFirstOrder(
                pos_variables,
                mona.Conjunction([pos_guard, chosen_vertical, others_empty]))
        return outer

    def one_in_pre(self) -> mona.Formula:
        substitution = {cast(Term, v): Variable(self.system,
                                                f"substitute_{v.name}")
                        for v in self.quantified_variables}
        try:
            renamed_broadcast = self.substitute(substitution)
        except FormulaError:
            raise FormulaError("Cannot generate formula for non-normalized"
                               + " Broadcast {self}")
        pos_variables = sorted([cast(mona.Variable, v.as_mona())
                                for v in self.quantified_variables], key=str)
        pos_guard = self.guard_as_mona()
        neg_variables = sorted([
            cast(mona.Variable, v.as_mona())
            for v in renamed_broadcast.quantified_variables], key=str)
        neg_guard = renamed_broadcast.guard_as_mona()
        inner = mona.UniversalFirstOrder(
                neg_variables,
                mona.Implication(
                    mona.Conjunction(
                        [neg_guard,
                         mona.Disjunction([
                             p.hit_pre()
                             for p in renamed_broadcast.body.predicates])]),
                    mona.Equal(cast(mona.Variable,
                                    substitution[self.variable].as_mona()),
                               cast(mona.Variable, self.variable.as_mona()))))
        outer = mona.ExistentialFirstOrder(
                pos_variables,
                mona.Conjunction([pos_guard]
                                 + [p.hit_pre()
                                    for p in self.body.predicates] + [inner]))
        return outer

    def one_in_post(self) -> mona.Formula:
        substitution = {cast(Term, v): Variable(self.system,
                                                f"substitute_{v.name}")
                        for v in self.quantified_variables}
        try:
            renamed_broadcast = self.substitute(substitution)
        except FormulaError:
            raise FormulaError("Cannot generate formula for non-normalized"
                               + " Broadcast {self}")
        pos_variables = sorted([cast(mona.Variable, v.as_mona())
                                for v in self.quantified_variables], key=str)
        pos_guard = self.guard_as_mona()
        neg_variables = sorted([
            cast(mona.Variable, v.as_mona())
            for v in renamed_broadcast.quantified_variables], key=str)
        neg_guard = renamed_broadcast.guard_as_mona()
        inner = mona.UniversalFirstOrder(
                neg_variables,
                mona.Implication(
                    mona.Conjunction(
                        [neg_guard,
                         mona.Disjunction([
                             p.hit_post()
                             for p in renamed_broadcast.body.predicates])]),
                    mona.Equal(cast(mona.Variable,
                                    substitution[self.variable].as_mona()),
                               cast(mona.Variable, self.variable.as_mona()))))
        outer = mona.ExistentialFirstOrder(
                pos_variables,
                mona.Conjunction([pos_guard]
                                 + [p.hit_post()
                                    for p in self.body.predicates] + [inner]))
        return outer

    def disjoint_all_pre(self) -> mona.Formula:
        guard = self.guard_as_mona()
        variables = sorted([cast(mona.Variable, v.as_mona())
                            for v in self.quantified_variables], key=str)
        inner = mona.Conjunction([p.miss_pre() for p in self.body.predicates])
        return mona.UniversalFirstOrder(variables, mona.Implication(guard,
                                                                    inner))

    def disjoint_all_post(self) -> mona.Formula:
        guard = self.guard_as_mona()
        variables = sorted([cast(mona.Variable, v.as_mona())
                            for v in self.quantified_variables], key=str)
        inner = mona.Conjunction([p.miss_post() for p in self.body.predicates])
        return mona.UniversalFirstOrder(variables, mona.Implication(guard,
                                                                    inner))

    def one_post(self) -> mona.Formula:
        guard = self.guard_as_mona()
        variables = sorted([cast(mona.Variable, v.as_mona())
                            for v in self.quantified_variables], key=str)
        all_hit = mona.Conjunction([p.hit_post()
                                    for p in self.body.predicates])
        return mona.ExistentialFirstOrder(
                variables,
                mona.Conjunction([guard, all_hit]))

    def vertical_hit(self) -> mona.Formula:
        guard = self.guard_as_mona()
        variables = sorted([cast(mona.Variable, v.as_mona())
                            for v in self.quantified_variables], key=str)
        pre_post_hit = mona.Conjunction([
            mona.Implication(p.hit_pre(), p.hit_post())
            for p in self.body.predicates])
        return mona.UniversalFirstOrder(
                variables,
                mona.Implication(guard, pre_post_hit))

    def is_dead(self) -> mona.Formula:
        variables = sorted([cast(mona.Variable, v.as_mona())
                            for v in self.quantified_variables], key=str)
        all_dead = mona.Conjunction([p.miss_pre()
                                     for p in self.body.predicates])
        complete_guard = self.guard_as_mona()
        return mona.ExistentialFirstOrder(
                variables,
                mona.Conjunction([complete_guard, all_dead]))

    def guard_as_mona(self) -> mona.Formula:
        return mona.Disjunction([
                mona.Conjunction(
                    [f.as_mona()
                     for f in cast(RestrictionCollection, c).restrictions])
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

    def invariant_predicate(self, number: int) -> mona.Formula:
        inner = mona.Disjunction([
            # disjoint pre and post
            mona.Conjunction([self.disjoint_all_pre(),
                              self.disjoint_all_post()]),
            # unique pre and post
            mona.Conjunction([self.one_in_pre(), self.one_in_post()]),
            # more than one in pre
            mona.Conjunction([mona.Negation(self.disjoint_all_pre()),
                              mona.Negation(self.one_in_pre())]),
            ])
        variables = sorted([cast(mona.Variable, v.as_mona())
                            for v in self.free_variables], key=str)  # type: ignore attr-defined  # noqa: E501
        guard = self.guard_as_mona()
        quantification = mona.UniversalFirstOrder(
                variables,
                mona.Implication(guard, inner))
        return mona.PredicateDefinition(
                f"invariant_transition_{number}",
                self.system.state_variables,
                [],
                quantification).simplify()

    def one_in_all_broadcasts_pre(self) -> mona.Formula:
        tmp = mona.Disjunction([
            mona.Conjunction(
                [b.one_in_pre()]
                + [o.disjoint_all_pre()
                   for j, o in enumerate(self.broadcasts) if i != j])
            for i, b in enumerate(self.broadcasts)])
        return tmp

    def one_in_all_broadcasts_post(self) -> mona.Formula:
        tmp = mona.Disjunction([
            mona.Conjunction(
                [b.one_in_post()]
                + [o.disjoint_all_post()
                   for j, o in enumerate(self.broadcasts) if i != j])
            for i, b in enumerate(self.broadcasts)])
        return tmp

    def one_in_pre(self) -> mona.Formula:
        return mona.Disjunction([
            mona.Conjunction([self.one_in_free_pre(),
                              self.disjoint_all_broadcasts_pre()]),
            mona.Conjunction([self.disjoint_all_free_pre(),
                              self.one_in_all_broadcasts_pre()])])

    def one_in_post(self) -> mona.Formula:
        return mona.Disjunction([
            mona.Conjunction([self.one_in_free_post(),
                              self.disjoint_all_broadcasts_post()]),
            mona.Conjunction([self.disjoint_all_free_post(),
                              self.one_in_all_broadcasts_post()])])

    def disjoint_all_broadcasts_pre(self) -> mona.Formula:
        return mona.Conjunction([b.disjoint_all_pre()
                                 for b in self.broadcasts])

    def disjoint_all_broadcasts_post(self) -> mona.Formula:
        return mona.Conjunction([b.disjoint_all_post()
                                 for b in self.broadcasts])

    def disjoint_all_free_pre(self) -> mona.Formula:
        return mona.Conjunction([p.miss_pre()
                                 for p in self.ports.predicates])

    def disjoint_all_free_post(self) -> mona.Formula:
        return mona.Conjunction([p.miss_post()
                                 for p in self.ports.predicates])

    def disjoint_all_pre(self) -> mona.Formula:
        return mona.Conjunction([self.disjoint_all_free_pre(),
                                 self.disjoint_all_broadcasts_pre()])

    def disjoint_all_post(self) -> mona.Formula:
        return mona.Conjunction([self.disjoint_all_free_post(),
                                 self.disjoint_all_broadcasts_post()])

    def one_in_free_pre(self) -> mona.Formula:
        return mona.Disjunction([
            mona.Conjunction([cast(mona.Formula, p.hit_pre())]
                             + [o.miss_pre()
                                for o in self.ports.predicates if o != p])
            for p in self.ports.predicates])

    def one_in_free_post(self) -> mona.Formula:
        return mona.Disjunction([
            mona.Conjunction([cast(mona.Formula, p.hit_post())]
                             + [o.miss_post()
                                for o in self.ports.predicates if o != p])
            for p in self.ports.predicates])

    def trap_predicate(self, number: int) -> mona.Formula:
        guard = self.guard_as_mona()
        variables = sorted([cast(mona.Variable, v.as_mona())
                            for v in self.free_variables], key=str)  # type: ignore attr-defined  # noqa: E501
        ports = self.ports.predicates
        free_pre = mona.Disjunction([p.hit_pre() for p in ports])
        free_post = mona.Disjunction([p.hit_post() for p in ports])
        safe_post: List[mona.Formula] = [free_post]

        broadcast_local: List[mona.Formula] = []
        if self.broadcasts:
            broadcasts_one_post = mona.Disjunction([b.one_post()
                                                    for b in self.broadcasts])
            safe_post.append(broadcasts_one_post)

            broadcasts_vertical = mona.Conjunction(
                    [cast(mona.Formula, mona.Negation(free_pre))] +
                    [b.vertical_hit() for b in self.broadcasts])
            broadcast_local.append(broadcasts_vertical)
        inner = mona.Disjunction([
            mona.Disjunction(safe_post),
            mona.Conjunction([mona.Negation(free_pre),
                              mona.Conjunction(broadcast_local)])
            ])
        formula = mona.UniversalFirstOrder(variables,
                                           mona.Implication(guard, inner))
        return mona.PredicateDefinition(f"trap_transition_{number}",
                                        self.system.state_variables,
                                        [], formula).simplify()

    def is_dead_predicate(self, number: int) -> mona.Formula:
        dead_free = mona.Disjunction(
                [p.miss_pre() for p in self.ports.predicates])
        dead_broadcasts = mona.Disjunction(
                [b.is_dead() for b in self.broadcasts])
        guard = self.guard_as_mona()
        inner = mona.Implication(
                guard,
                mona.Disjunction([dead_free, dead_broadcasts]))
        formula = mona.UniversalFirstOrder([cast(mona.Variable, v.as_mona())
                                            for v in self.free_variables],  # type: ignore attr-defined  # noqa: E501
                                           inner)
        return mona.PredicateDefinition(f"dead_transition_{number}",
                                        self.system.state_variables,
                                        [], formula).simplify()

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
        logger.debug(f"normalizing terms in clause {self}")
        local_terms = {t for t in self.all_terms  # type: ignore attr-defined # noqa: E501, F723
                       if (t.variables
                           and t.variables.issubset(self.free_variables))}  # type: ignore attr-defined # noqa: E501, F723
        constant_terms = {t for t in self.all_terms  # type: ignore attr-defined # noqa: E501, F723
                          if not t.variables}
        logger.debug(f"identifying local terms {local_terms}")
        logger.debug(f"identifying const terms {constant_terms}")
        sorted_vars = sorted([v for v in self.free_variables])  # type: ignore attr-defined # noqa: E501, F723
        renaming: Dict[Term, Variable] = {v: Variable(self.system, f"x_{i}")
                                          for i, v in enumerate(sorted_vars)}
        logger.debug(f"going over local terms with {renaming}")
        term_substitions = {}
        term_restrictions: Set[Restriction] = set()
        for term in local_terms:
            restrictions, variable = term.term_normalization(renaming)
            term_restrictions |= restrictions
            term_substitions[term] = variable
        logger.debug(f"gathered term restrictions {term_restrictions}"
                     + " and " + f" term substitutions: {term_substitions}")
        renaming.update(term_substitions)
        const_substitions = {}
        const_restrictions: Set[Restriction] = set()
        for term in constant_terms:
            restrictions, variable = term.term_normalization(renaming)
            const_restrictions |= restrictions
            const_substitions[term] = variable
        logger.debug(f"gathered constant restrictions {const_restrictions}"
                     + f" and constant substitutions: {const_substitions}")
        all_renames = dict(renaming)
        all_renames.update(const_substitions)
        broadcasts = []
        for j, broadcast in enumerate(self.broadcasts):
            replacement_variable = Variable(self.system, f"b_{j}")
            all_renames[broadcast.variable] = replacement_variable
            n_broadcast = broadcast.normalize(all_renames)
            broadcasts.append(n_broadcast)
        new_guard = RestrictionCollection(
                self.system,
                (self.guard.restrictions
                 | term_restrictions
                 | const_restrictions)).substitute(
                        renaming)
        new_ports = self.ports.substitute(all_renames)
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

    def invariant_predicate(self) -> mona.Formula:
        inner = mona.Conjunction([
            mona.PredicateCall(
                f"invariant_transition_{number}",
                self.system.state_variables)
            for number in range(1, len(self.clauses) + 1)])
        return mona.PredicateDefinition(
                f"invariant",
                self.system.state_variables,
                [],
                inner).simplify()

    def initially_uniquely_marked_flow_predicate(self) -> mona.Formula:
        inner = mona.Conjunction([
            mona.PredicateCall("invariant",
                               self.system.state_variables),
            mona.PredicateCall("uniquely_intersects_initial",
                               self.system.state_variables)])
        return mona.PredicateDefinition(
                "initially_uniquely_marked_flow",
                self.system.state_variables,
                [],
                inner).simplify()

    def flow_invariant_predicate(self) -> mona.Formula:
        flow_states = [mona.Variable(f"F{s}") for s in self.system.states]
        precondition = mona.PredicateCall(
                "initially_uniquely_marked_flow",
                flow_states)
        postcondition = mona.PredicateCall(
                "unique_intersection",
                flow_states + self.system.state_variables)
        return mona.PredicateDefinition(
                "flow_invariant",
                self.system.state_variables,
                [], mona.UniversalSecondOrder(
                    flow_states, mona.Implication(precondition, postcondition))
                ).simplify()

    def marking_predicate(self) -> mona.Formula:
        m = mona.Variable("m")
        unique_in_component = mona.UniversalFirstOrder(
                [m],
                mona.Conjunction([
                    mona.Disjunction([
                        mona.Conjunction(
                            [cast(mona.Formula, mona.ElementIn(m, pos))]
                            + [cast(mona.Formula, mona.ElementNotIn(m, neg))
                               for neg in c.state_variables
                               if neg != pos])
                        for pos in c.state_variables])
                    for c in self.system.components]))
        flow_invariant = mona.PredicateCall("flow_invariant",
                                            self.system.state_variables)
        trap_invariant = mona.PredicateCall("trap_invariant",
                                            self.system.state_variables)
        return mona.PredicateDefinition(
                "marking",
                self.system.state_variables,
                [],
                mona.Conjunction([
                    unique_in_component,
                    flow_invariant,
                    trap_invariant,
                ])).simplify()

    def custom_property(self, name: str, formula: str) -> mona.Formula:
        return mona.PredicateDefinition(
                name,
                self.system.state_variables,
                [],
                mona.RawFormula(formula)).simplify()

    def render_base_theory(self) -> str:
        template = env.get_template("base-theory.mona")
        return template.render(interaction=self)

    def render_property_unreachability(
            self,
            property_name: str,
            cached_base_theory: Optional[str] = None) -> str:
        base_theory = (cached_base_theory if cached_base_theory
                       else self.render_base_theory())
        template = env.get_template("proof-script.mona")
        return template.render(
                interaction=self,
                base_theory=base_theory,
                property_name=property_name)

    def property_check(self, property_name: str) -> mona.Formula:
        return mona.PredicateCall(property_name, self.system.state_variables)

    def marking_predicate_call(self) -> mona.Formula:
        return mona.PredicateCall("marking", self.system.state_variables)

    @property
    def property_names(self) -> List[str]:
        return sorted(list(self.properties.keys()) + ["deadlock"])

    def normalize(self) -> "Interaction":
        return Interaction([c.normalize() for c in self.clauses],
                           self.system,
                           self.assumptions,
                           self.properties)

    def trap_predicate(self) -> mona.Formula:
        inner = mona.Conjunction(
                [mona.PredicateCall(f"trap_transition_{number}",
                                    self.system.state_variables)
                 for number in range(1, len(self.clauses) + 1)])
        return mona.PredicateDefinition(
                "trap",
                self.system.state_variables,
                [],
                inner).simplify()

    def deadlock_predicate(self) -> mona.Formula:
        inner = mona.Conjunction(
                [mona.PredicateCall(f"dead_transition_{number}",
                                    self.system.state_variables)
                 for number in range(1, len(self.clauses) + 1)])
        return mona.PredicateDefinition(
                "deadlock",
                self.system.state_variables,
                [],
                inner).simplify()

    def initially_marked_trap_predicate(self) -> mona.Formula:
        inner = mona.Conjunction([
            mona.PredicateCall("trap",
                               self.system.state_variables),
            mona.PredicateCall("intersects_initial",
                               self.system.state_variables)])
        return mona.PredicateDefinition(
                "initially_marked_trap",
                self.system.state_variables,
                [],
                inner).simplify()

    def trap_invariant_predicate(self) -> mona.Formula:
        trap_states = [mona.Variable(f"T{s}") for s in self.system.states]
        precondition = mona.PredicateCall("initially_marked_trap", trap_states)
        postcondition = mona.PredicateCall(
                "intersection",
                trap_states + self.system.state_variables)
        return mona.PredicateDefinition(
                "trap_invariant",
                self.system.state_variables,
                [],
                mona.UniversalSecondOrder(trap_states,
                                          mona.Implication(precondition,
                                                           postcondition))
                ).simplify()

    def intersection_predicate(self) -> mona.Formula:
        x = mona.Variable("x")
        one_states = [mona.Variable(f"one{s}") for s in self.system.states]
        two_states = [mona.Variable(f"two{s}") for s in self.system.states]
        in_both_states = cast(List[mona.Formula],
                              [mona.Conjunction([mona.ElementIn(x, o),
                                                 mona.ElementIn(x, t)])
                               for o, t in zip(one_states, two_states)])
        quantified_formula = mona.ExistentialFirstOrder(
                [x], mona.Disjunction(in_both_states))
        return mona.PredicateDefinition("intersection",
                                        one_states + two_states,
                                        [], quantified_formula
                                        ).simplify()

    def unique_intersection_predicate(self) -> mona.Formula:
        x = mona.Variable("x")
        y = mona.Variable("y")
        one_states = [mona.Variable(f"one{s}") for s in self.system.states]
        two_states = [mona.Variable(f"two{s}") for s in self.system.states]
        pairs = list(zip(one_states, two_states))

        statements: List[mona.Formula] = []
        # fix x in intersection of one state:
        for pair in pairs:
            pos = [cast(mona.Formula, mona.ElementIn(x, state))
                   for state in pair]
            different_pairs = [p for p in pairs if p != pair]
            neg = [  # negated statement from above
                    cast(mona.Formula, mona.Negation(
                        mona.Conjunction(
                            [mona.ElementIn(x, state) for state in pair])))
                    # for all other pairs
                    for pair in different_pairs]
            statements.append(mona.Conjunction(pos + neg))
        fix_x = mona.Disjunction(statements)
        # make sure x is unique:
        # y is in intersection
        y_in_intersection = mona.Disjunction([
            mona.Conjunction([mona.ElementIn(y, state) for state in pair])
            for pair in pairs])
        # y is x if y is in intersection
        unique_x = mona.UniversalFirstOrder(
                [y],
                mona.Implication(y_in_intersection, mona.Equal(x, y)))
        formula = mona.ExistentialFirstOrder([x], mona.Conjunction([fix_x,
                                                                    unique_x]))
        return mona.PredicateDefinition(
                "unique_intersection",
                one_states + two_states, [], formula).simplify()

    def intersects_initial_predicate(self) -> mona.Formula:
        x = mona.Variable("x")
        initial_states = [mona.Variable(c.initial_state)
                          for c in self.system.components]
        x_initial = mona.Disjunction(
                [mona.ElementIn(x, init) for init in initial_states])
        formula = mona.ExistentialFirstOrder([x], x_initial)
        return mona.PredicateDefinition("intersects_initial",
                                        self.system.state_variables,
                                        [], formula).simplify()

    def uniquely_intersects_initial_predicate(self) -> mona.Formula:
        x = mona.Variable("x")
        y = mona.Variable("y")
        initial_states = [mona.Variable(c.initial_state)
                          for c in self.system.components]
        statements: List[mona.Formula] = []
        for init in initial_states:
            other_initial_states = [i for i in initial_states if i != init]
            x_only_in_init = mona.Conjunction(
                    [cast(mona.Formula, mona.ElementIn(x, init))]
                    + [cast(mona.Formula, mona.ElementNotIn(x, i))
                       for i in other_initial_states])
            statements.append(x_only_in_init)
        x_in_only_one_initial = mona.Disjunction(statements)
        y_in_initial = mona.Disjunction(
                [mona.ElementIn(y, i) for i in initial_states])
        x_unique = mona.UniversalFirstOrder([y], mona.Implication(
            y_in_initial, mona.Equal(x, y)))
        formula = mona.ExistentialFirstOrder(
                [x],
                mona.Conjunction([x_in_only_one_initial, x_unique]))
        return mona.PredicateDefinition(
                "uniquely_intersects_initial",
                self.system.state_variables, [], formula).simplify()

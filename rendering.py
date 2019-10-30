from functools import wraps

from mona import *
from system import *
from formula import Clause, Broadcast, Predicate

import jinja2

env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('mona-templates/')
    )

def add_function(jinja_filter):
    name = jinja_filter.__name__
    env.globals[name]=jinja_filter

@add_function
def intersection_predicate(system: System) -> str:
    x = Variable("x")
    one_states = [Variable(f"one{s}") for s in system.states]
    two_states = [Variable(f"two{s}") for s in system.states]
    in_both_states = [ Conjunction([ElementIn(x, o), ElementIn(x, t)])
            for o, t in zip(one_states, two_states) ]
    quantified_formula = ExistentialFirstOrder(x, Disjunction(in_both_states))
    return PredicateDefinition("intersection", one_states + two_states, [],
            quantified_formula).render()

@add_function
def unique_intersection_predicate(system: System) -> str:
    x = Variable("x")
    y = Variable("y")
    one_states = [Variable(f"one{s}") for s in system.states]
    two_states = [Variable(f"two{s}") for s in system.states]
    pairs = list(zip(one_states, two_states))

    statements = []
    # fix x in intersection of one state:
    for pair in pairs:
        pos = [ElementIn(x, state) for state in pair]
        different_pairs = [p for p in pairs if p != pair]
        neg = [ # negated statement from above
                Negation(Conjunction([ElementIn(x, state) for state in pair]))
                # for all other pairs
                for pair in different_pairs]
        statements.append(Conjunction(pos + neg))
    fix_x = Disjunction(statements)
    # make sure x is unique:
    ## y is in intersection
    y_in_intersection = Disjunction([
        Conjunction([ElementIn(y, state) for state in pair])
        for pair in pairs])
    ## y is x if y is in intersection
    unique_x = UniversalFirstOrder(y,
            Implication(y_in_intersection, Equal(x, y)))
    formula = ExistentialFirstOrder(x, Conjunction([fix_x, unique_x]))
    return PredicateDefinition("unique_intersection",
        one_states + two_states, [], formula).render()

@add_function
def intersects_initial_predicate(system: System) -> str:
    x = Variable("x")
    initial_states = [Variable(c.initial_state) for c in system.components]
    x_initial = Disjunction([ElementIn(x, init) for init in initial_states])
    formula = ExistentialFirstOrder(x, x_initial)
    return PredicateDefinition("intersects_initial", system.states, [],
            formula).render()

@add_function
def uniquely_intersects_initial_predicate(system: System) -> str:
    x = Variable("x")
    y = Variable("y")
    initial_states = [Variable(c.initial_state) for c in system.components]
    statements = []
    for init in initial_states:
        other_initial_states = [i for i in initial_states if i != init]
        x_only_in_init = Conjunction([ElementIn(x, init)] + [ElementNotIn(x, i)
            for i in other_initial_states])
        statements.append(x_only_in_init)
    x_in_only_one_initial = Disjunction(statements)
    y_in_initial = Disjunction([ElementIn(y, i) for i in initial_states])
    x_unique = UniversalFirstOrder(y, Implication(y_in_initial, Equal(x, y)))
    formula = ExistentialFirstOrder(x,
            Conjunction([x_in_only_one_initial, x_unique]))
    return PredicateDefinition("uniquely_intersects_initial", system.states, [],
            formula).render()


def _hit_pre(predicate: Predicate):
    return ElementIn(predicate.argument.to_mona(), predicate.pre)

def _hit_post(predicate: Predicate):
    return ElementIn(predicate.argument.to_mona(), predicate.post)

def _miss_pre(predicate: Predicate):
    return ElementNotIn(predicate.argument.to_mona(), predicate.pre)

def _miss_post(predicate: Predicate):
    return ElementNotIn(predicate.argument.to_mona(), predicate.post)

def _broadcast_guard_and_terms(broadcast: Broadcast):
    term_constraints = Conjunction([t.mona_constraint()
        for t in broadcast.complex_terms])
    return Conjunction([term_constraints, broadcast.guard.to_mona()])

def _broadcast_dead(broadcast: Broadcast):
    variables = [broadcast.variable.to_mona()] + [t.to_mona()
            for t in broadcast.complex_terms]
    all_dead = Conjunction([_miss_pre(p) for p in broadcast.body.predicates])
    complete_guard = _broadcast_guard_and_terms(broadcast)
    return ExistentialFirstOrder(variables,
            Conjunction([complete_guard, all_dead]))

def _clause_guard_and_terms(clause: Clause):
    term_constraints = Conjunction(
            [t.mona_constraint() for t in clause.complex_free_terms])
    guard = Conjunction([clause.guard.to_mona(), term_constraints])
    return guard

def _clause_quantified_objects(clause: Clause):
    variables = [v.to_mona() for v in clause.free_variables]
    variables += [t.to_mona() for t in clause.complex_free_terms]
    return variables

@add_function
def transition_dead_predicate(system: System, clause: Clause,
        number: int) -> str:
    dead_free = Disjunction([_miss_pre(p) for p in clause.ports.predicates])
    dead_broadcasts = Disjunction([_broadcast_dead(b) for b in clause.broadcasts])
    guard = _clause_guard_and_terms(clause)
    inner = Implication(guard, Disjunction([dead_free, dead_broadcasts]))
    formula = UniversalFirstOrder(_clause_quantified_objects(clause), inner)
    return PredicateDefinition(f"dead_transition_{number}", system.states, [],
        formula).render()

def _broadcast_one_post(broadcast: Broadcast):
    guard = _broadcast_guard_and_terms(broadcast)
    variables = [broadcast.variable.to_mona()] + [t.to_mona()
            for t in broadcast.complex_terms]
    all_hit = Conjunction([_hit_post(p) for p in broadcast.body.predicates])
    return ExistentialFirstOrder(variables, Conjunction([guard, all_hit]))

def _broadcast_vertical(broadcast: Broadcast):
    guard = _broadcast_guard_and_terms(broadcast)
    variables = [broadcast.variable.to_mona()] + [t.to_mona()
            for t in broadcast.complex_terms]
    pre_post_hit = Conjunction([
        Implication(_hit_pre(p), _hit_post(p))
        for p in broadcast.body.predicates])
    return UniversalFirstOrder(variables, Implication(guard, pre_post_hit))

@add_function
def transition_trap_predicate(system: System, clause: Clause,
        number: int) -> str:
    guard = _clause_guard_and_terms(clause)
    variables = _clause_quantified_objects(clause)
    trap_in_free = Implication(
            Disjunction([_hit_pre(p) for p in clause.ports.predicates]),
            Disjunction([_hit_post(p) for p in clause.ports.predicates]))
    broadcasts_one_post = Disjunction([_broadcast_one_post(b)
        for b in clause.broadcasts])
    broadcasts_vertical = Conjunction([_broadcast_vertical(b)
        for b in clause.broadcasts])
    formula = UniversalFirstOrder(variables, Implication(guard,
        Disjunction([trap_in_free, broadcasts_one_post, broadcasts_vertical])))
    return PredicateDefinition(f"trap_transition_{number}", system.states, [],
            formula).render()

def render_base_theory(system: System) -> str:
    template = env.get_template("base-theory.mona")
    return template.render(system=system)

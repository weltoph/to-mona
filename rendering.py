from functools import wraps

import mona
import system
import formula

import jinja2

env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('mona-templates/')
    )

def add_function(jinja_filter):
    name = jinja_filter.__name__
    env.globals[name]=jinja_filter

@add_function
def intersection_predicate(system: system.System) -> str:
    x = mona.Variable("x")
    one_states = [mona.Variable(f"one{s}") for s in system.states]
    two_states = [mona.Variable(f"two{s}") for s in system.states]
    in_both_states = [ mona.Conjunction(
        [mona.ElementIn(x, o), mona.ElementIn(x, t)])
            for o, t in zip(one_states, two_states) ]
    quantified_formula = mona.ExistentialFirstOrder(x,
            mona.Disjunction(in_both_states))
    return mona.PredicateDefinition("intersection", one_states + two_states,
            [], quantified_formula).render()

@add_function
def unique_intersection_predicate(system: system.System) -> str:
    x = mona.Variable("x")
    y = mona.Variable("y")
    one_states = [mona.Variable(f"one{s}") for s in system.states]
    two_states = [mona.Variable(f"two{s}") for s in system.states]
    pairs = list(zip(one_states, two_states))

    statements = []
    # fix x in intersection of one state:
    for pair in pairs:
        pos = [mona.ElementIn(x, state) for state in pair]
        different_pairs = [p for p in pairs if p != pair]
        neg = [ # negated statement from above
                mona.Negation(
                    mona.Conjunction(
                        [mona.ElementIn(x, state) for state in pair]))
                # for all other pairs
                for pair in different_pairs]
        statements.append(mona.Conjunction(pos + neg))
    fix_x = mona.Disjunction(statements)
    # make sure x is unique:
    ## y is in intersection
    y_in_intersection = mona.Disjunction([
        mona.Conjunction([mona.ElementIn(y, state) for state in pair])
        for pair in pairs])
    ## y is x if y is in intersection
    unique_x = mona.UniversalFirstOrder(y,
            mona.Implication(y_in_intersection, mona.Equal(x, y)))
    formula = mona.ExistentialFirstOrder(x, mona.Conjunction([fix_x, unique_x]))
    return mona.PredicateDefinition("unique_intersection",
        one_states + two_states, [], formula).render()

@add_function
def intersects_initial_predicate(system: system.System) -> str:
    x = mona.Variable("x")
    initial_states = [mona.Variable(c.initial_state)
            for c in system.components]
    x_initial = mona.Disjunction(
            [mona.ElementIn(x, init) for init in initial_states])
    formula = mona.ExistentialFirstOrder(x, x_initial)
    return mona.PredicateDefinition("intersects_initial", system.states, [],
            formula).render()

@add_function
def uniquely_intersects_initial_predicate(system: system.System) -> str:
    x = mona.Variable("x")
    y = mona.Variable("y")
    initial_states = [mona.Variable(c.initial_state)
            for c in system.components]
    statements = []
    for init in initial_states:
        other_initial_states = [i for i in initial_states if i != init]
        x_only_in_init = mona.Conjunction(
                [mona.ElementIn(x, init)]
                + [mona.ElementNotIn(x, i) for i in other_initial_states])
        statements.append(x_only_in_init)
    x_in_only_one_initial = mona.Disjunction(statements)
    y_in_initial = mona.Disjunction(
            [mona.ElementIn(y, i) for i in initial_states])
    x_unique = mona.UniversalFirstOrder(y, mona.Implication(
        y_in_initial, mona.Equal(x, y)))
    formula = mona.ExistentialFirstOrder(x,
            mona.Conjunction([x_in_only_one_initial, x_unique]))
    return mona.PredicateDefinition("uniquely_intersects_initial",
            system.states, [], formula).render()


def _hit_pre(predicate: formula.Predicate):
    return mona.ElementIn(mona.translate_term(predicate.argument),
            predicate.pre)

def _hit_post(predicate: formula.Predicate):
    return mona.ElementIn(mona.translate_term(predicate.argument),
            predicate.post)

def _miss_pre(predicate: formula.Predicate):
    return mona.ElementNotIn(mona.translate_term(predicate.argument),
            predicate.pre)

def _miss_post(predicate: formula.Predicate):
    return mona.ElementNotIn(mona.translate_term(predicate.argument),
            predicate.post)

def _broadcast_dead(broadcast: formula.Broadcast):
    variables = ([mona.translate_term(broadcast.variable)]
            + [mona.translate_term(t) for t in broadcast.complex_terms])
    all_dead = mona.Conjunction(
            [_miss_pre(p) for p in broadcast.body.predicates])
    complete_guard = mona.translate_guard_and_terms(broadcast)
    return mona.ExistentialFirstOrder(variables,
            mona.Conjunction([complete_guard, all_dead]))

@add_function
def transition_dead_predicate(system: system.System, clause: formula.Clause,
        number: int) -> str:
    dead_free = mona.Disjunction(
            [_miss_pre(p) for p in clause.ports.predicates])
    dead_broadcasts = mona.Disjunction(
            [_broadcast_dead(b) for b in clause.broadcasts])
    guard = mona.translate_guard_and_terms(clause)
    inner = mona.Implication(guard,
            mona.Disjunction([dead_free, dead_broadcasts]))
    formula = mona.UniversalFirstOrder(mona.get_quantifiable_objects(clause),
            inner)
    return mona.PredicateDefinition(f"dead_transition_{number}", system.states,
            [], formula).render()

def _broadcast_one_post(broadcast: formula.Broadcast):
    guard = mona.translate_guard_and_terms(broadcast)
    variables = mona.get_quantifiable_objects(broadcast)
    all_hit = mona.Conjunction(
            [_hit_post(p) for p in broadcast.body.predicates])
    return mona.ExistentialFirstOrder(variables,
            mona.Conjunction([guard, all_hit]))

def _broadcast_vertical(broadcast: formula.Broadcast):
    guard = mona.translate_guard_and_terms(broadcast)
    variables = mona.get_quantifiable_objects(broadcast)
    pre_post_hit = mona.Conjunction([
        mona.Implication(_hit_pre(p), _hit_post(p))
        for p in broadcast.body.predicates])
    return mona.UniversalFirstOrder(variables,
            mona.Implication(guard, pre_post_hit))

@add_function
def transition_trap_predicate(system: system.System, clause: formula.Clause,
        number: int) -> str:
    guard = mona.translate_guard_and_terms(clause)
    variables = mona.get_quantifiable_objects(clause)
    trap_in_free = mona.Implication(
            mona.Disjunction([_hit_pre(p)  for p in clause.ports.predicates]),
            mona.Disjunction([_hit_post(p) for p in clause.ports.predicates]))
    inner = trap_in_free
    if clause.broadcasts:
        broadcasts_one_post = mona.Disjunction([_broadcast_one_post(b)
            for b in clause.broadcasts])
        broadcasts_vertical = mona.Conjunction([_broadcast_vertical(b)
            for b in clause.broadcasts])
        inner = mona.Disjunction(
            [trap_in_free, broadcasts_one_post, broadcasts_vertical])
    formula = mona.UniversalFirstOrder(variables,
            mona.Implication(guard, inner))
    return mona.PredicateDefinition(f"trap_transition_{number}", system.states,
            [], formula).render()

@add_function
def trap_predicate(system: system.System):
    inner = mona.Conjunction([mona.PredicateCall(f"trap_transition_{number}",
        system.states) for number in range(1, len(system.interaction) + 1)])
    return mona.PredicateDefinition("trap", system.states, [], inner).render()

@add_function
def deadlock_predicate(system: system.System):
    inner = mona.Conjunction([mona.PredicateCall(f"dead_transition_{number}",
        system.states) for number in range(1, len(system.interaction) + 1)])
    return mona.PredicateDefinition("deadlock", system.states, [],
            inner).render()

@add_function
def trap_invariant(system: system.System):
    trap_states = [mona.Variable(f"T{s}") for s in system.states]
    precondition = mona.Conjunction([mona.PredicateCall("trap", trap_states),
        mona.PredicateCall("intersects_initial", trap_states)])
    postcondition = mona.PredicateCall("intersection",
            trap_states + system.states)
    return mona.UniversalSecondOrder(trap_states,
            mona.Implication(precondition, postcondition)).render()

def render_base_theory(system: system.System) -> str:
    template = env.get_template("base-theory.mona")
    return template.render(system=system)


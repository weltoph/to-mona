from functools import wraps

from mona import *
from system import *

import jinja2

env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('mona-templates/')
    )

def add_filter(jinja_filter):
    print(f"adding {jinja_filter.__name__}")
    env.filters[jinja_filter.__name__] = jinja_filter

@add_filter
def intersection_predicate(system: System) -> str:
    x = Variable("x")
    one_states = [Variable(f"one{s}") for s in system.states]
    two_states = [Variable(f"two{s}") for s in system.states]
    in_both_states = [ Conjunction([ElementIn(x, o), ElementIn(x, t)])
            for o, t in zip(one_states, two_states) ]
    quantified_formula = ExistentialFirstOrder(x, Disjunction(in_both_states))
    return PredicateDefinition("intersection", one_states + two_states, [],
            quantified_formula).render()

@add_filter
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
    # make sure x is unique
    # y is in intersection
    y_in_intersection = Disjunction([
        Conjunction([ElementIn(y, state) for state in pair])
        for pair in pairs])
    # y is x if y is in intersection
    unique_x = UniversalFirstOrder(y,
            Implication(y_in_intersection, Equal(x, y)))
    formula = ExistentialFirstOrder(x, Conjunction([fix_x, unique_x]))
    return PredicateDefinition("unique_intersection",
        one_states + two_states, [], formula).render()

@add_filter
def intersects_initial_predicate(system: System) -> str:
    x = Variable("x")
    initial_states = [Variable(c.initial_state) for c in system.components]
    x_initial = Disjunction([ElementIn(x, init) for init in initial_states])
    formula = ExistentialFirstOrder(x, x_initial)
    return PredicateDefinition("intersects_initial", system.states, [],
            formula).render()

@add_filter
def uniquely_intersects_initial_predicate(system: System):
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

def render_base_theory(system: System) -> str:
    template = env.get_template("base-theory.mona")
    return template.render(system=system)

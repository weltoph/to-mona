from typing import List, Tuple, Dict, Optional

from formula import *
from bounded import *
from system import *

from tempfile import NamedTemporaryFile

import datetime

class MonaError(Exception):
    pass

@dataclass
class Model:
    n: int
    distribution: Dict[str, List[int]]

    def __post_init__(self):
        self.agents = list(range(0, self.n))

    def __str__(self):
        result = f"n: {self.n}\n"
        for name, elements in self.distribution.items():
            elms = ', '.join([str(e) for e in elements])
            result += f"{name}: {{{elms}}}\n"
        return result

    def mona_definition(self):
        stmts = []
        for name, elements in self.distribution.items():
            negatives = [v for v in self.agents if v not in elements]
            stmts += [f"({e} in {name})" for e in elements]
            stmts += [f"({e} notin {name})" for e in negatives]
        return " & ".join(stmts)

@dataclass
class Result:
    property_name: str
    proof_script: str
    model: Optional[Model]
    proof_time: datetime.timedelta
    creating_proof_script_time: datetime.timedelta
    mona_time: datetime.timedelta
    extracting_model_time: datetime.timedelta

    @property
    def success(self) -> bool:
        return not self.model

@dataclass
class Analysis:
    filename: str
    formula: BoundedInteraction

    def __post_init__(self):
        start_theory = datetime.datetime.now()
        self.theory = theory(self.formula)
        self.theory_generation = datetime.datetime.now() - start_theory
        self.results = []
        if len(self.filename) <= 20:
            self.filename_short = self.filename
        elif '/' in self.filename:
            self.filename_short = self.filename[self.filename.rfind('/'):][:20]
        else:
            self.filename_short = self.filename[:20]

    def _create_proof_script(self, property: str, minimal_amount) -> str:
        template = env.get_template('property_proof.mona')
        script = template.render(test=property, theory=self.theory,
                minimal_amount=minimal_amount, formula=self.formula)
        return write_tmp_file(script)

    def perform_test(self, property: str, minimal_amount: int = 2):
        start_test = datetime.datetime.now()

        start_proof_script = datetime.datetime.now()
        proof_script = self._create_proof_script(property, minimal_amount)
        delta_proof_script = datetime.datetime.now() - start_proof_script

        start_mona_call = datetime.datetime.now()
        mona_result = call_mona(proof_script)
        delta_mona_call = datetime.datetime.now() - start_mona_call

        start_model = datetime.datetime.now()
        model = extract_model(mona_result)
        delta_model = datetime.datetime.now() - start_model

        delta_overall = datetime.datetime.now() - start_test

        result = Result(property, proof_script, model, delta_overall,
                delta_proof_script, delta_mona_call, delta_model)
        self.results.append(result)

        return not model

    def print_statistics(self, without_header=False, small=True):
        header = ["filename",
                "property",
                "success",
                "script",
                "time",
                "proof_script",
                "mona",
                "model",
                ]
        if small:
            header = header[:5]
        row_format ="{:<22}"*len(header)
        if not without_header:
            print(row_format.format(*header))
            print("-"*20*7)
        for result in self.results:
            results = [
                f"{self.filename_short}",
                f"{result.property_name}",
                f"{result.success}",
                f"{result.proof_script}",
                f"{(result.proof_time+self.theory_generation).total_seconds()}s",
                f"{result.creating_proof_script_time.total_seconds()}s",
                f"{result.mona_time.total_seconds()}s",
                f"{result.extracting_model_time.total_seconds()}s"
                ]
            if small:
                results = results[:5]
            print(row_format.format(*results))

import jinja2

env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('mona-templates/')
    )


def render_constant(constant: Constant) -> str:
    return constant.value

def render_variable(variable: Variable) -> str:
    return variable.name

def render_successor(successor: Successor) -> str:
    return f"succ_{render_term(successor.argument)}"


def render_term(obj):
    mona_renderer = {
            Constant: render_constant,
            Variable: render_variable,
            Successor: render_successor
    }
    return mona_renderer[type(obj)](obj)

# inject specific functions for use in jinja templates
env.globals.update(render_term=render_term)
env.filters['render_term_filter'] = render_term

def disjoint_region(clause: BoundedClause) -> str:
    template = env.get_template('transition_disjoint_region.mona')
    rendered = template.render(clause=clause)
    return rendered

def uniquely_intersects_region(clause: BoundedClause) -> str:
    template = env.get_template('transition_uniquely_intersects_region.mona')
    rendered = template.render(clause=clause)
    return rendered

def dead(clause: BoundedClause) -> str:
    template = env.get_template('transition_dead.mona')
    return template.render(clause=clause)

def trap(formula: BoundedInteraction) -> str:
    template = env.get_template('trap.mona')
    return template.render(formula=formula)

def invariant(formula: BoundedInteraction) -> str:
    template = env.get_template('invariant.mona')
    return template.render(formula=formula)

def intersection(formula: BoundedInteraction) -> str:
    template = env.get_template('intersection.mona')
    return template.render(formula=formula)

def unique_intersection(formula: BoundedInteraction) -> str:
    template = env.get_template('unique_intersection.mona')
    return template.render(formula=formula)

def intersects_initial(formula: BoundedInteraction) -> str:
    template = env.get_template('intersects_initial.mona')
    return template.render(formula=formula)

def uniquely_intersects_initial(formula: BoundedInteraction) -> str:
    template = env.get_template('uniquely_intersects_initial.mona')
    return template.render(formula=formula)

def marking(formula: BoundedInteraction) -> str:
    template = env.get_template('marking.mona')
    return template.render(formula=formula)

def constraints(formula: BoundedInteraction) -> str:
    template = env.get_template('constraints.mona')
    return template.render(formula=formula)

def deadlock(formula: BoundedInteraction) -> str:
    template = env.get_template('deadlock.mona')
    return template.render(formula=formula)

def render_property(formula: BoundedInteraction, name: str, content: str) -> str:
    template = env.get_template('property.mona')
    return template.render(formula=formula, name=name, content=content)

def theory(formula: BoundedInteraction) -> str:
    theory = "\n".join(
            [disjoint_region(c) for c in formula.clauses]
            + [uniquely_intersects_region(c) for c in formula.clauses]
            + [dead(c) for c in formula.clauses]
            + [
                unique_intersection(formula),
                intersects_initial(formula),
                uniquely_intersects_initial(formula),
                trap(formula),
                invariant(formula),
                intersection(formula),
                marking(formula),
                constraints(formula),
            ]
            + [
                render_property(formula, name, content) for name, content
                in formula.properties.items()
            ]
            )
    template = env.get_template('theory.mona')
    return template.render(theory_content=theory, formula=formula)

def call_mona(scriptfile: str) -> str:
    from subprocess import run
    mona_cmnd = f"mona -q {scriptfile}"
    result = run([mona_cmnd], capture_output=True, shell=True,
            encoding="utf-8")
    if result.returncode != 0:
        msg = f"something went wrong when running {mona_cmnd}:\n{result.stdout}"
        raise MonaError(msg)
    return result.stdout

def write_tmp_file(content: str) -> str:
    with NamedTemporaryFile(mode = "w", delete = False) as tmp_file:
        print(content, file=tmp_file, flush=True)
        return tmp_file.name

def list_all_models(formula: BoundedInteraction, description: str, size: int) -> List[Model]:
    theory_desc = theory(formula)
    found_models = []
    template = env.get_template('model_list.mona')
    while True:
        script = template.render(
                formula=formula,
                theory=theory_desc,
                size=size,
                description=description,
                found_models=[m.mona_definition() for m in found_models])
        tmp_file = write_tmp_file(script)
        result = call_mona(tmp_file)
        model = extract_model(result)
        if model:
            found_models.append(model)
        else:
            break
    return found_models

def extract_model(mona_output: str) -> Optional[Model]:
    if "Formula is unsatisfiable" in mona_output: return None
    import itertools
    import lark
    model_grammar = """
        start: "n = " INT [assignment]+
        assignment: NAME "=" set
        set: empty | "{" int_list "}"
        empty: "{}"

        int_list: INT | INT "," int_list

        %import common.INT
        %import common.CNAME -> NAME
        %import common.WS
        %ignore WS
    """
    class Transformation(lark.Transformer):
        def __init__(self):
            self.assignments = []

        def empty(self, args):
            return []

        def int_list(self, args):
            new_value = int(args.pop(0))
            if not args:
                return [new_value]
            other_values = args.pop()
            other_values.append(new_value)
            return sorted(other_values)

        def set(self, args):
            return args.pop()

        def assignment(self, args):
            name = str(args.pop(0))
            elements = args.pop(0)
            self.assignments.append((name, elements))

        def start(self, args):
            n = int(args.pop(0))
            return Model(n, dict(self.assignments))

    model_parser = lark.Lark(model_grammar)


    lines = list(itertools.dropwhile(lambda l: l,
            itertools.dropwhile(lambda l: not "A satisfying example" in l,
                mona_output.split("\n"))))[1:-1]
    model_description = '\n'.join(lines)
    model = Transformation().transform(model_parser.parse(model_description))
    return model


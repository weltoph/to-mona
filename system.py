from typing import List, Set, Optional, Tuple, Dict
from dataclasses import dataclass
from formula import Clause
from enum import Enum, unique

class SystemDefinitionError(Exception):
    pass

@dataclass
class Component:
    name: str
    initial_state: str
    transitions: List[Tuple[str, str, str]]

    def __str__(self) -> str:
        return f"Component {self.name} {self.transitions}"

    def __post_init__(self):
        collection_by_label = {}
        states = set()
        found_initial = False
        for s, l, t in self.transitions:
            collection_by_label.setdefault(l, []).append((s, t))
            states.add(s)
            states.add(t)
            if self.initial_state == s:
                found_initial = True
        if not found_initial:
            raise SystemDefinitionError("initial state has no outgoing transition")
        for l in collection_by_label:
            transitions = collection_by_label[l]
            if len(transitions) != 1:
                raise SystemDefinitionError(
                        f"transitions {transitions} share label {l}")
            else:
                collection_by_label[l] = transitions.pop()
        # TODO: maybe check for connectivity
        self.transition_by_label = collection_by_label
        self.states = sorted(list(states))

    @property
    def number_of_states(self) -> int:
        return len(self.states)

    @property
    def labels(self) -> Set[str]:
        return set(self.transition_by_label.keys())

    @property
    def number_of_labels(self) -> int:
        return len(self.labels)

    def edge_with_label(self, label: str) -> Optional[Tuple[str, str]]:
        return self.transition_by_label.get(label, None)

    def source_of_label(self, label: str) -> Optional[str]:
        try:
            self.edge_with_label(label)[0]
        except TypeError:
            return None

    def target_of_label(self, label: str) -> Optional[str]:
        try:
            self.edge_with_label(label)[1]
        except TypeError:
            return None

@unique
class SystemAddition(Enum):
    PROPERTY = "property"
    PREDICATE = "assumption"

@dataclass
class System:
    components: List[Component]
    interaction: List[Clause]
    predicates: Dict[str, Tuple[str, str]]
    properties: Dict[str, str]

    @property
    def property_names(self) -> List[str]:
        return sorted(list(self.properties.keys()) + ["deadlock"])

    def __post_init__(self):
        self.components_of_labels = {
                l: c for c in self.components
                     for l in c.labels
            }
        all_labels = set(self.components_of_labels.keys())
        sum_of_labels = sum([c.number_of_labels for c in self.components])
        if len(all_labels) != sum_of_labels:
            raise SystemDefinitionError(f"Not disjoint labels in components!")
        for clause in self.interaction:
            for predicate in clause.predicates:
                edge = self.edge_with_label(predicate.name)
                if not edge:
                    raise SystemDefinitionError(
                            f"{predicate.name} unknown in system")
                predicate.bind(*edge)

    @property
    def states(self) -> Set[str]:
        return sum([c.states for c in self.components], [])

    def edge_with_label(self, label: str) -> Optional[Tuple[str, str]]:
        try:
            component = self.components_of_labels[label]
            return component.edge_with_label(label)
        except KeyError:
            return None

    def origin_of_label(self, label: str) -> Optional[str]:
        edge = self.edge_with_label(label)
        if not edge:
            return None
        return edge[0]

    def target_of_label(self, label: str) -> Optional[str]:
        edge = self.edge_with_label(label)
        if not edge:
            return None
        return edge[1]

from typing import List, Set, Optional, Tuple
from dataclasses import dataclass

class SystemDefinitionError(Exception):
    pass

@dataclass
class Component:
    name: str
    initial_state: str
    transitions: List[Tuple[str, str, str]]
    critical_states: List[str]

    def __str__(self) -> str:
        return f"Component {self.name} {self.transitions}"

    def __post_init__(self):
        # prefix states with component name making them unique:
        self.transitions = [(f"{self.name}_{s}", l, f"{self.name}_{t}")
                for s, l, t in self.transitions]
        self.initial_state = f"{self.name}_{self.initial_state}"
        self.critical_states = [f"{self.name}_{s}" for s in self.critical_states]

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

@dataclass
class System:
    components: List[Component]

    def __post_init__(self):
        self.components_of_labels = {
                l: c for c in self.components
                     for l in c.labels
            }
        all_labels = set(self.components_of_labels.keys())
        sum_of_labels = sum([c.number_of_labels for c in self.components])
        if len(all_labels) != sum_of_labels:
            raise SystemDefinitionError(f"Not disjoint labels in components!")

    @property
    def states(self) -> Set[str]:
        return sum([c.states for c in self.components], [])

    @property
    def has_critical_sections(self) -> bool:
        return any([bool(c.critical_states) for c in self.components])

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

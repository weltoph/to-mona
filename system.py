from typing import Set, Optional, Tuple, cast, FrozenSet, List
from dataclasses import dataclass
from enum import Enum, unique

import mona


class SystemDefinitionError(Exception):
    pass


@dataclass(frozen=True)
class Component:
    name: str
    initial_state: str
    transitions: FrozenSet[Tuple[str, str, str]]

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
            raise SystemDefinitionError(
                    "initial state has no outgoing transition")
        for l in collection_by_label:
            transitions = collection_by_label[l]
            if len(transitions) != 1:
                raise SystemDefinitionError(
                        f"transitions {transitions} share label {l}")
            else:
                collection_by_label[l] = transitions.pop()
        # TODO: maybe check for connectivity
        object.__setattr__(self, 'transition_by_label', collection_by_label)
        object.__setattr__(self, 'states', sorted(list(states)))

    @property
    def state_variables(self) -> List[mona.Variable]:
        return sorted([mona.Variable(s) for s in self.states], key=str)  # type: ignore attr-defined  # noqa: E501, F723

    @property
    def number_of_states(self) -> int:
        return len(self.states)  # type: ignore

    @property
    def labels(self) -> Set[str]:
        return set(self.transition_by_label.keys())  # type: ignore

    @property
    def number_of_labels(self) -> int:
        return len(self.labels)  # type: ignore

    def edge_with_label(self, label: str) -> Optional[Tuple[str, str]]:
        return self.transition_by_label.get(label, None)  # type: ignore

    def source_of_label(self, label: str) -> Optional[str]:
        potential_edge = self.edge_with_label(label)
        if potential_edge is not None:
            edge = cast(Tuple[str, str], potential_edge)
            return edge[0]
        else:
            return None

    def target_of_label(self, label: str) -> Optional[str]:
        potential_edge = self.edge_with_label(label)
        if potential_edge is not None:
            edge = cast(Tuple[str, str], potential_edge)
            return edge[1]
        else:
            return None


@unique
class SystemAddition(Enum):
    PROPERTY = "property"
    ASSUMPTION = "assumption"


@dataclass(frozen=True)
class System:
    components: FrozenSet[Component]

    def __post_init__(self):
        components_of_labels = {
                l: c
                for c in self.components
                for l in c.labels
            }
        object.__setattr__(self, 'components_of_labels',
                           components_of_labels)
        all_labels = set(self.components_of_labels.keys())
        sum_of_labels = sum([c.number_of_labels for c in self.components])
        if len(all_labels) != sum_of_labels:
            raise SystemDefinitionError(f"Not disjoint labels in components!")

    @property
    def states(self) -> Set[str]:
        return set(sum([c.states for c in self.components],  # type: ignore
                       []))

    @property
    def state_variables(self) -> List[mona.Variable]:
        return sorted([mona.Variable(s) for s in self.states], key=str)

    def edge_with_label(self, label: str) -> Optional[Tuple[str, str]]:
        try:
            component = self.components_of_labels[label]  # type: ignore
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

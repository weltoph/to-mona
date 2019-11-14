from dataclasses import dataclass

from typing import Set, Any, Optional, FrozenSet, Tuple


class ProcessnetError(Exception):
    def __init__(self, msg):
        self.msg = msg


@dataclass
class Indexable:
    identification_number: int
    value: Any = None
    host_process: Optional["Process"] = None

    def __post_init__(self):
        self.comp_str: str = (str(self.value) if self.value is not None
                              else str(self.identification_number))
        if not self.host_process:
            parent_index: Tuple[str, ...] = tuple()
        else:
            parent_index: Tuple[str, ...] = self.host_process.full_index
        self.full_index: Tuple[int, ...] = (parent_index
                                            + (self.identification_number,))

    @property
    def all_leaves(self) -> Set["Place"]:
        raise NotImplementedError()

    def get(self, query: str, separator: str = "/") -> "Indexable":
        query_list = query.split(separator)
        rest_query = separator.join(query_list[1:])
        try:
            next_index = query_list[0]
            for process in self.children:
                if next_index == process.comp_str:
                    return process.get(rest_query, separator=separator)
            raise ProcessnetError(f"Cannot find {next_index} in {self}")
        except IndexError:
            return self

    def get_regex(self, query: str, separator: str = "/") -> Set["Indexable"]:
        from re import compile
        query_list = query.split(separator)
        rest_query = separator.join(query_list[1:])
        try:
            next_index = query_list[0]
            regex = compile(next_index)
            found_elements = [
                    process.get_regex(rest_query, separator=separator)
                    for process in self.children
                    if regex.match(process.comp_str)]
            all_elements: Set["Indexable"] = set()
            for e in found_elements:
                all_elements |= e
            return all_elements
        except IndexError:
            return {self}

    @property
    def children(self) -> Set["Indexable"]:
        raise NotImplementedError()

    @property
    def full_name(self) -> Tuple[str, ...]:
        parent_name = (tuple() if not self.host_process
                       else self.host_process.full_name)
        return parent_name + (str(self),)

    def __hash__(self):
        return hash(self.full_index)

    def __eq__(self, other):
        try:
            return (type(self) == type(other)
                    and self.host_process == other.host_process
                    and (self.identification_number
                         == other.identification_number))
        except AttributeError:
            return False

    def __str__(self):
        if self.value is not None:
            return f"Process<{self.identification_number}>({self.value})"
        else:
            return f"Process<{self.identification_number}>"


@dataclass
class Place(Indexable):
    def all_leaves(self) -> Set["Place"]:
        return {self}


@dataclass
class Process(Indexable):
    def __post_init__(self):
        super().__post_init__()
        self._children: Set[Indexable] = set()
        self.places: Set[Place] = set()

    @property
    def children(self) -> Set[Indexable]:
        return self._children

    def all_leaves(self) -> Set["Place"]:
        all_leaves: Set["Place"] = set()
        for c in self._children:
            all_leaves |= c.all_leaves
        return all_leaves

    def add_child_process(self, value: Any = None) -> "Process":
        new_process = Process(len(self._children), value, self)
        self._children.add(new_process)
        return new_process

    def add_place(self, value: Any = None) -> Place:
        new_place = Place(len(self.places), value, self)
        self.places.add(new_place)
        return new_place


@dataclass
class Transition:
    preset: FrozenSet[Place]
    postset: FrozenSet[Place]

    def __hash__(self):
        return hash(self.preset) & hash(self.postset)

    def __eq__(self, other):
        try:
            return (type(self) == type(other)
                    and self.preset == other.preset
                    and self.postset == other.postset)
        except AttributeError:
            return False

    def __str__(self):
        preset = ", ".join([str(p) for p in self.preset])
        postset = ", ".join([str(p) for p in self.postset])
        return f"{{ {preset} }} ->  {self} -> {{ {postset} }}"


@dataclass
class PetriNet:
    root_process: Process

    def __post_init__(self):
        self.transitions = set()

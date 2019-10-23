from formula import *
from system import System

@dataclass
class BoundedPort(Port):
    bound_to: System

    def __post_init__(self):
        self.origin, self.target = self.bound_to.edge_with_label(self.name)
        if not self.origin or not self.target:
            error = f"cannot bind {self} to {self.bound_to}:"
            msg = f"missing label {self.name}"
            raise FormulaError(f"{error}: {msg}")

    def rename(self, renaming) -> "BoundedPort":
        return BoundedPort(self.name, self.argument.rename(renaming),
                self.bound_to)

    @classmethod
    def bind_to(cls, port: Port, to: System):
        return cls(port.name, port.argument, to)

@dataclass
class BoundedBroadcast(Broadcast):
    port: BoundedPort
    bound_to: System

    def rename(self, renaming) -> "BoundedBroadcast":
        return BoundedBroadcast(
                self.variable.rename(renaming),
                self.guard.rename(renaming),
                self.port.rename(renaming),
                self.index,
                self.bound_to)

    @classmethod
    def bind_to(cls, broadcast: Broadcast, to: System):
        return BoundedBroadcast(
                broadcast.variable,
                broadcast.guard,
                BoundedPort.bind_to(broadcast.port, to),
                broadcast.index,
                to)

@dataclass
class BoundedClause(Clause):
    ports: List[BoundedPort]
    broadcasts: List[BoundedBroadcast]
    bound_to: System

    @classmethod
    def bind_to(cls, clause: Clause, to: System):
        return BoundedClause(
                clause.variables,
                clause.guard,
                [BoundedPort.bind_to(p, to) for p in clause.ports],
                [BoundedBroadcast.bind_to(b, to) for b in clause.broadcasts],
                clause.index,
                to)

@dataclass
class BoundedInteraction(Interaction):
    clauses: List[BoundedClause]
    bound_to: System

    @classmethod
    def bind_to(cls, interaction: Interaction, to: System):
        return BoundedInteraction(
                [BoundedClause.bind_to(c, to) for c in interaction.clauses],
                to)


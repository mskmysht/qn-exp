from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory
from sequence.entanglement_management.generation import EntanglementGenerationA
from dataclasses import dataclass

@dataclass
class MemoryParams:
    fidelity: float
    frequency: float
    efficiency: float
    coherence_time: float
    wavelength: float

class EntalngleGenNode(Node):
    def __init__(self, name, tl: Timeline, memory_params: MemoryParams):
        super().__init__(name, tl)
        memory = Memory(f"{name}.memo", tl, **memory_params.__dict__)
        memory.owner = self
        memory.add_receiver(self)
        self.add_component(memory)

def main():
    pass

if __name__ == "__main__":
    main()

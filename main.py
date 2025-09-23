from sequence.kernel.timeline import Timeline
from sequence.message import Message
from sequence.topology.node import Node, BSMNode
from sequence.components.bsm import SingleAtomBSM
from sequence.components.memory import Memory
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.components.photon import Photon
from sequence.entanglement_management.generation import EntanglementGenerationA

from dataclasses import dataclass


@dataclass
class MemoryParams:
    fidelity: float
    frequency: float
    efficiency: float
    coherence_time: float
    wavelength: int


class SimpleManager:
    def __init__(self):
        self.raw_count = 0
        self.ent_count = 0

    def update(self, protocol, memory: Memory, state: str):
        if state == "RAW":
            self.raw_count += 1
        else:
            self.ent_count += 1


class EntalngleGenNode(Node):
    def __init__(self, name, tl: Timeline, memory_params: MemoryParams):
        super().__init__(name, tl)
        memory = Memory(
            f"{self.name}.memo",
            tl,
            memory_params.fidelity,
            memory_params.frequency,
            memory_params.efficiency,
            memory_params.coherence_time,
            memory_params.wavelength,
        )
        memory.owner = self
        memory.add_receiver(self)
        self.memory = memory
        self.add_component(memory)

        self.resource_manager = SimpleManager()

    def setup_protocols(self, middle: str, other: str):
        self.protocols = [
            EntanglementGenerationA.create(
                self, f"{self.name}.eg", middle, other, self.memory
            )
        ]

    def init(self):
        self.memory.reset()

    def receive_message(self, src: str, msg: Message) -> None:
        self.protocols[0].received_message(src, msg)  # type: ignore

    def get(self, photon: Photon, **kwargs):  # type: ignore
        self.send_qubit(kwargs["dst"], photon)


def pair_protocol(n1: EntalngleGenNode, n2: EntalngleGenNode):
    p1 = n1.protocols[0]
    p2 = n2.protocols[0]
    p1.set_others(p2.name, n2.name, [n2.memory.name])
    p2.set_others(p1.name, n1.name, [n1.memory.name])


def main():
    mp = MemoryParams(0.9, 2e3, 1, -1, 500)
    tl = Timeline()
    n1 = EntalngleGenNode("n1", tl, mp)
    n2 = EntalngleGenNode("n2", tl, mp)
    bsm_node = BSMNode("bsm", tl, [n1.name, n2.name])
    bsm: SingleAtomBSM = bsm_node.get_components_by_type(SingleAtomBSM)[0]
    bsm.update_detectors_params("efficiency", 1)

    qc1 = QuantumChannel("qc1", tl, attenuation=0, distance=1000)
    qc2 = QuantumChannel("qc2", tl, attenuation=0, distance=1000)
    qc1.set_ends(n1, bsm_node.name)
    qc2.set_ends(n2, bsm_node.name)

    nodes = [n1, n2, bsm_node]
    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if i == j:
                continue
            n = nodes[i]
            m = nodes[j]
            cc = ClassicalChannel(f"cc_{n.name}_{m.name}", tl, 1000, 100_000_000)
            cc.set_ends(n, m.name)

    n1.setup_protocols(bsm_node.name, n2.name)
    n2.setup_protocols(bsm_node.name, n1.name)
    pair_protocol(n1, n2)

    n1_memo = n1.memory
    print("before", n1_memo.entangled_memory, n1_memo.fidelity)

    tl.init()
    n1.protocols[0].start()
    n2.protocols[0].start()
    tl.run()
    print("after", n1_memo.entangled_memory, n1_memo.fidelity)


if __name__ == "__main__":
    main()

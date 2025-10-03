from dataclasses import dataclass
from typing import Any, Callable

import sequence
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
from sequence.resource_management.rule_manager import Arguments, Rule
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.components.memory import Memory, MemoryArray
from sequence.components.bsm import SingleAtomBSM
from sequence.topology.node import QuantumRouter
from sequence.resource_management.resource_manager import (
    ResourceManager,
    ResourceManagerMessage,
)
from sequence.resource_management.memory_manager import MemoryInfo, MemoryManager
from sequence.network_management.reservation import (
    ResourceReservationProtocol,
    Reservation,
)
from sequence.app.random_request import RandomRequestApp

import sequence.utils.log as log

from prettytable import PrettyTable


class CustomMemoryManager:
    def __init__(self, inner: MemoryManager):
        self.__inner = inner
        # self.ent_count = 0
        # self.raw_count = 0
        # self.occupied_count = 0
        self.indices: list[int] = []
        self.trans_curr_states: list[str] = []
        self.trans_next_states: list[str] = []
        self.trans_curr_remote_memos: list[str | None] = []
        self.trans_next_remote_memos: list[str | None] = []
        self.trans_ticks: list[int] = []

    def update(self, memory: Memory, state: str) -> None:
        self.trans_ticks.append(int(memory.timeline.now()))
        info = self.__inner.get_info_by_memory(memory)
        self.indices.append(info.index)
        self.trans_curr_states.append(info.state)
        self.trans_next_states.append(state)
        self.trans_curr_remote_memos.append(info.remote_memo)
        self.trans_next_remote_memos.append(memory.entangled_memory["memo_id"])

        self.__inner.update(memory, state)
        # if state == "RAW":
        #     self.raw_count += 1
        # elif state == "ENTANGLED":
        #     self.ent_count += 1
        # else:
        #     self.occupied_count += 1

    def set_resource_manager(self, resource_manager: ResourceManager) -> None:
        return self.__inner.set_resource_manager(resource_manager)

    def __len__(self):
        return len(self.__inner)

    def __getitem__(self, item: int) -> MemoryInfo:
        return self.__inner.__getitem__(item)

    def get_info_by_memory(self, memory: Memory) -> MemoryInfo:
        return self.__inner.get_info_by_memory(memory)

    def get_memory_by_name(self, memory_name: str) -> Memory:
        return self.__inner.get_memory_by_name(memory_name)


def load_network(path: str) -> RouterNetTopo:
    topo = RouterNetTopo(path)
    for node in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        qr: QuantumRouter = node  # type: ignore
        if qr.resource_manager is not None:
            cmm = CustomMemoryManager(qr.resource_manager.get_memory_manager())
            qr.resource_manager.memory_manager = cmm  # type: ignore
    return topo


@dataclass
class MemoryParams:
    frequency: float
    coherence_time: float
    efficiency: float
    fidelity: float


@dataclass
class SwapParams:
    success_prob: float
    degradation: float


@dataclass
class DetectorParams:
    efficiency: float
    count_rate: float
    time_resolution: float


@dataclass
class QChannelParams:
    attenuation: float
    qc_frequency: float


def set_parameters(
    topo: RouterNetTopo,
    memo_params: MemoryParams,
    swap_params: SwapParams,
    detector_params: DetectorParams,
    qchannel_params: QChannelParams,
):
    for _node in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        qr: QuantumRouter = _node  # type: ignore
        mem_arr: MemoryArray = qr.get_components_by_type(MemoryArray)[0]
        for key, value in memo_params.__dict__.items():
            mem_arr.update_memory_params(key, value)

        rsvp: ResourceReservationProtocol = qr.network_manager.protocol_stack[1]  # type: ignore
        rsvp.set_swapping_success_rate(swap_params.success_prob)
        rsvp.set_swapping_degradation(swap_params.degradation)

    for bsm_node in topo.get_nodes_by_type(RouterNetTopo.BSM_NODE):
        bsm: SingleAtomBSM = bsm_node.get_components_by_type(SingleAtomBSM)[0]
        for key, value in detector_params.__dict__.items():
            bsm.update_detectors_params(key, value)

    for qc in topo.get_qchannels():
        qc.attenuation = qchannel_params.attenuation
        qc.frequency = qchannel_params.qc_frequency


def request(topo: RouterNetTopo, e0: str, e1: str, memory_size: int = 25):
    start_node_name = e0
    end_node_name = e1
    n0: QuantumRouter | None = None
    n1: QuantumRouter | None = None

    for router in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == start_node_name:
            n0 = router  # type: ignore
        elif router.name == end_node_name:
            n1 = router  # type: ignore
    assert n0 is not None and n1 is not None

    nm = n0.network_manager
    assert nm is not None
    nm.request(
        n1.name,
        start_time=1_000_000_000_000,
        end_time=10_000_000_000_000,
        memory_size=memory_size,
        target_fidelity=0.9,
    )

    return (n0, n1)


def show_memories(router: QuantumRouter):
    assert router.resource_manager is not None

    print(router.name, "memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for info in router.resource_manager.memory_manager:
        if info.remote_node is not None:
            print(
                f"{info.index:6}\t{info.remote_node:15}\t{info.fidelity:0.7f}:\t{info.entangle_time * 1e-12}"
            )


def run(
    json_path: str,
    end_node_names: list[str],
    min_memo_size: int = 1,
    max_memo_size: int = 5,
):
    memo_params = MemoryParams(
        frequency=2e3,
        coherence_time=0,
        efficiency=1.0,
        fidelity=0.9,
    )
    swap_params = SwapParams(
        success_prob=0.9,
        degradation=0.99,
    )
    detector_params = DetectorParams(
        efficiency=0.9,
        count_rate=50_000_000,
        time_resolution=100,
    )
    qchannel_params = QChannelParams(
        attenuation=1e-5,
        qc_frequency=1e11,
    )

    topo = load_network(json_path)
    set_parameters(topo, memo_params, swap_params, detector_params, qchannel_params)

    tl = topo.get_timeline()
    log.set_logger(__name__, tl)
    log.set_logger_level("DEBUG")
    # log.track_module("memory_manager")

    # n1, _ = request(topo, "end1", "end2", 12)
    # n3, _ = request(topo, "end3", "end4", 13)
    apps: list[RandomRequestApp] = []
    end_nodes: list[QuantumRouter] = [r for r in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER) if r.name in end_node_names]  # type: ignore
    router_names = [end_node.name for end_node in end_nodes]
    for i, router in enumerate(end_nodes):
        other_routers = router_names[:i] + router_names[i + 1 :]
        app = RandomRequestApp(
            router,
            other_routers,
            i + 10,
            min_dur=400_000_000_000,
            max_dur=500_000_000_000,
            min_size=min_memo_size,
            max_size=max_memo_size,  # exclusive
            min_fidelity=0.8,
            max_fidelity=0.85,
        )
        apps.append(app)
        app.start()

    tl.init()
    tl.run()

    # for app in apps:
    #     print(f"node {app.node.name}")
    #     print(f"\treservations: {app.reserves}")
    #     print(f"\tthroughput: {app.all_throughput}")

    print("\nReservations Table:")

    num_path_crossed: dict[str, int] = {}

    tbl = PrettyTable(
        [
            "Id",
            "Initiator",
            "Responder",
            "Path",
            "Memory size",
            "Start time (s)",
            "End time (s)",
        ]
    )
    for node in end_nodes:
        p: ResourceReservationProtocol = node.network_manager.protocol_stack[1]  # type: ignore
        for _res in p.accepted_reservations:
            res: Reservation = _res  # type: ignore
            if node.name != res.initiator:
                continue
            tbl.add_row(
                [
                    res.identity,
                    res.initiator,
                    res.responder,
                    res.path,
                    res.memory_size,
                    res.start_time * 1e-12,
                    res.end_time * 1e-12,
                ]
            )
            for n in res.path:
                num_path_crossed.setdefault(n, 0)
                num_path_crossed[n] += res.memory_size

    print(tbl)

    # mem_tbl = PrettyTable(
    #     [
    #         "Node",
    #         "Raw count",
    #         "Entangled count",
    #         "Occupied count",
    #         "Number of paths",
    #     ]
    # )
    import polars as pl

    df = pl.DataFrame()
    for router in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        mm: CustomMemoryManager = router.resource_manager.memory_manager  # type: ignore
        ddf = pl.DataFrame(
            [
                pl.Series("tick", mm.trans_ticks, dtype=pl.Int64),
                pl.Series("index", mm.indices, dtype=pl.Int32),
                pl.Series("curr_state", mm.trans_curr_states, dtype=pl.Utf8),
                pl.Series("next_state", mm.trans_next_states, dtype=pl.Utf8),
                pl.Series(
                    "remote_curr_memo", mm.trans_curr_remote_memos, dtype=pl.Utf8
                ),
                pl.Series(
                    "remote_next_memo", mm.trans_next_remote_memos, dtype=pl.Utf8
                ),
            ]
        )
        if not ddf.is_empty():
            df = df.vstack(ddf.with_columns(pl.lit(router.name).alias("node_name")))
        # mem_tbl.add_row(
        #     [
        #         router.name,
        #         mm.raw_count,
        #         mm.ent_count,
        #         mm.occupied_count,
        #         num_path_crossed.get(router.name, 0),
        #     ]
        # )
    # print(mem_tbl)
    df.write_csv(f"log_memory_transactions.csv")
    # print(df.lazy().filter(pl.col("node_name") == "r6").collect())

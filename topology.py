import networkx as nx
import math
import numpy.random as rnd
from dataclasses import dataclass, asdict
from typing import Literal
import json


@dataclass
class Node:
    name: str
    seed: int
    memo_size: int
    type: Literal["QuantumRouter"] = "QuantumRouter"


@dataclass
class QConnection:
    node1: str
    node2: str
    attenuation: float
    distance: float
    type: Literal["meet_in_the_middle"] = "meet_in_the_middle"


@dataclass
class CConnection:
    node1: str
    node2: str
    delay: float


@dataclass
class Top:
    is_parallel: bool
    stop_time: int
    nodes: list[Node]
    qconnections: list[QConnection]
    cconnections: list[CConnection]


def generate():
    n = 20
    g = nx.cycle_graph(n)
    rng = rnd.default_rng(0)

    m = 5
    temp = 0
    while temp < m:
        i = rng.integers(0, n)
        j = rng.integers(0, n)
        if i != j and not g.has_edge(i, j):
            g.add_edge(i, j)
            temp += 1

    radius = 1000
    for i, j in g.edges:
        k = min(i - j, j - i) % n
        # length of bottom line of an isosceles triangle with angle 2 k pi / n
        g.edges[i, j]["length"] = 2 * radius * math.sin(math.pi / n * k)

    nx.write_edgelist(g, "ring.edgelist")

    memo_size = 20

    nodes = [Node(f"r{i}", i, memo_size) for i in range(n)]
    qcons = [
        QConnection(f"r{i}", f"r{j}", 2e-3, g.edges[i, j]["length"]) for i, j in g.edges
    ]
    ccons = [
        CConnection(
            f"r{i}", f"r{j}", nx.shortest_path_length(g, i, j, weight="length") * 1e6
        )
        for i in range(n - 1)
        for j in range(i + 1, n)
    ]

    top = Top(
        is_parallel=False,
        stop_time=6_000_000_000_000,
        nodes=nodes,
        qconnections=qcons,
        cconnections=ccons,
    )

    jsonstr = json.dumps(asdict(top), indent=4)
    with open("ring.json", "w") as f:
        f.write(jsonstr)

    print(g.degree)


def metrics():
    import numpy as np

    g = nx.read_edgelist("ring.edgelist")
    bc: dict[str, float] = nx.betweenness_centrality(g)
    bc_values = np.array([bc[f"{i}"] for i in range(g.number_of_nodes())])
    idxs = np.argsort(bc_values)[::-1]
    for i in idxs:
        print(f"BC({i:2}): {bc_values[i]}")


if __name__ == "__main__":
    # generate()
    metrics()

import networkx as nx
from itertools import combinations
import numpy as np
import polars as pl


def metrics(path: str):
    g: nx.Graph = nx.read_edgelist(path, nodetype=int)
    bc: dict[int, float] = nx.betweenness_centrality(g)
    bc_values = np.array([bc[i] for i in range(g.number_of_nodes())])
    bc_idxs = np.argsort(bc_values)[::-1]
    for i in bc_idxs:
        print(f"BC({i:2}): {bc_values[i]}")

    cc: dict[int, float] = nx.closeness_centrality(g)
    cc_values = np.array([cc[i] for i in range(g.number_of_nodes())])
    cc_idxs = np.argsort(cc_values)[::-1]
    for i in cc_idxs:
        print(f"CC({i:2}): {cc_values[i]}")

    combs = []
    vcs = []
    cc_mean = []
    cc_var = []
    for ns in combinations(range(g.number_of_nodes()), 4):
        combs.append(ns)
        vcdict = nx.voronoi_cells(g, set(ns))
        vcs.append(np.fromiter((len(vcdict[n]) for n in ns), dtype=int).var())
        cc_mean.append(np.fromiter((cc[n] for n in ns), dtype=float).mean())
        cc_var.append(np.fromiter((cc[n] for n in ns), dtype=float).var())

    pl.Config.set_fmt_table_cell_list_len(-1)

    df = pl.DataFrame(
        {
            "comb": combs,
            "vc": vcs,
            "cc_mean": cc_mean,
            "cc_var": cc_var,
        }
    )
    # cc_mean = np.array(cc_mean)
    # vcs = np.array(vcs)

    # cc_mean_idxs = np.argsort(cc_mean)[::-1]
    # vc_idxs = np.argsort(vcs[cc_mean_idxs])

    # for i in cc_mean_idxs[vc_idxs][:5]:
    #     print(vcs[i], combs[i], f"{cc_mean[i]:.5f}", sep="\t")
    print(df.sort(by=["vc", "cc_mean"], descending=[False, True]).head(10))

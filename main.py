import typer
from typing_extensions import Annotated

import demo
import net
import topology.generator as gen

app = typer.Typer()


@app.command(name="demo")
def run_demo():
    demo.run()


@app.command()
def exp(
    json_path: str,
    end_node_names: Annotated[
        str, typer.Argument(help="Comma-separated list of end node names")
    ],
):
    # simple.run()
    # net.run("net.json", end_node_names=["end1", "end2", "end3", "end4"])
    # order by the sizes of voronoi cells
    # net.run("ring.json", end_node_names=["r0", "r3", "r10", "r12"])
    # order of C.C. scores
    net.run(json_path, end_node_names=end_node_names.split(","))


@app.command()
def generate(name: str, node_size: int, attach_edges: int):
    gen.generate_ba(name=name, node_size=node_size, attach_edges=attach_edges, seed=0)


if __name__ == "__main__":
    app()

import simple
import net


def main():
    # simple.run()
    # net.run("net.json", except_nodes=["center"])
    net.run("ring.json", end_node_names=["r0", "r5", "r10", "r15"])


if __name__ == "__main__":
    main()

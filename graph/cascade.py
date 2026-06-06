"""
Cascade simulator for the Ripple project.
Uses cuGraph BFS to compute affected nodes from disruption propagation.
"""
import cugraph
import cudf


def run_cascade(G: cugraph.Graph, start_node: int, max_depth: int = 15) -> cudf.DataFrame:
    """
    Runs BFS from start_node on cuGraph G.
    Returns cuDF DataFrame with columns [node, distance] for all reachable nodes
    within max_depth hops.

    Args:
        G: A cuGraph.Graph object
        start_node: The starting node for BFS traversal
        max_depth: Maximum depth (hops) to traverse. Default 15.

    Returns:
        cuDF DataFrame with columns ['node', 'distance'] containing all nodes
        reachable within max_depth hops from start_node.
    """
    distances = cugraph.bfs(G, start_vertex=start_node)
    affected = distances[distances["distance"] <= max_depth].copy()
    return affected[["vertex", "distance"]].rename(columns={"vertex": "node"})


def run_cascade_multi(G: cugraph.Graph, start_nodes: list[int], max_depth: int = 15) -> cudf.DataFrame:
    """
    Runs BFS from multiple start nodes (e.g. a disruption spanning multiple road nodes).
    Returns union of all affected nodes, taking minimum distance per node.

    Args:
        G: A cuGraph.Graph object
        start_nodes: List of starting nodes for BFS traversal
        max_depth: Maximum depth (hops) to traverse. Default 15.

    Returns:
        cuDF DataFrame with columns ['node', 'distance'] containing the union of
        all affected nodes from all start_nodes, with distance set to the minimum
        distance from any start node.
    """
    frames = [run_cascade(G, node, max_depth) for node in start_nodes]
    combined = cudf.concat(frames)
    return combined.groupby("node").agg({"distance": "min"}).reset_index()

"""
Loads the London road network from GraphML (OSMnx format) into cuGraph.
Also exposes nearest_node() for mapping disruption coordinates → graph nodes.
"""
from pathlib import Path
import math
import networkx as nx
import osmnx as ox
import cugraph
import cudf
import pandas as pd

DATA = Path(__file__).parent.parent / "data"
_GRAPHML = DATA / "london_road_network.graphml"


def nx_to_cugraph(G_nx: nx.DiGraph) -> tuple[cugraph.Graph, dict]:
    """
    Converts a NetworkX DiGraph to cuGraph.
    Returns (cugraph.Graph, node_map) where node_map[int_id] = original_node_id.
    """
    nodes = list(G_nx.nodes())
    node_to_int = {n: i for i, n in enumerate(nodes)}
    int_to_node = {i: n for n, i in node_to_int.items()}

    src = [node_to_int[u] for u, v in G_nx.edges()]
    dst = [node_to_int[v] for u, v in G_nx.edges()]
    edges_df = cudf.DataFrame({"src": src, "dst": dst})

    G_cu = cugraph.Graph(directed=True)
    G_cu.from_cudf_edgelist(edges_df, source="src", destination="dst")
    return G_cu, int_to_node


def build_node_positions(G_nx: nx.DiGraph, node_to_int: dict) -> pd.DataFrame:
    """Returns DataFrame with node_id (int), lat, lon for nearest_node lookups."""
    rows = []
    for node, int_id in node_to_int.items():
        data = G_nx.nodes[node]
        rows.append({"node_id": int_id, "lat": data.get("y", 0), "lon": data.get("x", 0)})
    return pd.DataFrame(rows)


def nearest_node(lat: float, lon: float, node_positions: pd.DataFrame) -> int:
    """Returns the int node_id of the nearest graph node to (lat, lon)."""
    dlat = node_positions["lat"] - lat
    dlon = node_positions["lon"] - lon
    dist = dlat**2 + dlon**2
    return int(node_positions.loc[dist.idxmin(), "node_id"])


def load_graph() -> tuple[cugraph.Graph, dict, pd.DataFrame]:
    """
    Main entry point. Loads GraphML → cuGraph.
    Returns (G_cu, int_to_node, node_positions_df)
    """
    if not _GRAPHML.exists():
        raise FileNotFoundError(f"Road network not found at {_GRAPHML}. Run scripts/download_road_network.py first.")
    print("Loading road network from GraphML...")
    G_nx = ox.load_graphml(_GRAPHML)
    print(f"  NetworkX graph: {len(G_nx.nodes)} nodes, {len(G_nx.edges)} edges")
    node_to_int = {n: i for i, n in enumerate(G_nx.nodes())}
    int_to_node = {i: n for n, i in node_to_int.items()}
    print("Converting to cuGraph...")
    G_cu, _ = nx_to_cugraph(G_nx)
    node_positions = build_node_positions(G_nx, node_to_int)
    print(f"  cuGraph ready: {G_cu.number_of_vertices()} vertices, {G_cu.number_of_edges()} edges")
    return G_cu, int_to_node, node_positions

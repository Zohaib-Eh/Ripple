import pytest
from unittest.mock import patch, MagicMock
import networkx as nx
import cudf
import cugraph


def make_small_nx():
    G = nx.DiGraph()
    G.add_nodes_from([0, 1, 2, 3])
    G.add_edges_from([(0, 1), (1, 2), (2, 3), (0, 3)])
    for n in G.nodes:
        G.nodes[n]['x'] = -0.1 + n * 0.01
        G.nodes[n]['y'] = 51.5 + n * 0.01
    return G


def test_nx_to_cugraph_has_correct_node_count():
    from graph.builder import nx_to_cugraph
    G_nx = make_small_nx()
    G_cu, node_map = nx_to_cugraph(G_nx)
    assert isinstance(G_cu, cugraph.Graph)
    assert len(node_map) == 4


def test_nx_to_cugraph_has_correct_edge_count():
    from graph.builder import nx_to_cugraph
    G_nx = make_small_nx()
    G_cu, node_map = nx_to_cugraph(G_nx)
    # 4 edges
    assert G_cu.number_of_edges() == 4


def test_nearest_node_returns_correct_index():
    from graph.builder import nearest_node
    import pandas as pd
    # nodes at lat/lon positions
    node_positions = pd.DataFrame({
        'node_id': [0, 1, 2],
        'lat': [51.50, 51.51, 51.52],
        'lon': [-0.10, -0.11, -0.12]
    })
    # Query point very close to node 1
    result = nearest_node(51.510, -0.110, node_positions)
    assert result == 1

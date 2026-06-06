import pytest
import cugraph
import cudf


def make_line_graph(n=10):
    """Linear graph: 0-1-2-3-...-n"""
    edges_df = cudf.DataFrame({
        "src": list(range(n - 1)),
        "dst": list(range(1, n))
    })
    G = cugraph.Graph(directed=False)
    G.from_cudf_edgelist(edges_df, source="src", destination="dst")
    return G


def test_bfs_cascade_returns_affected_nodes():
    from graph.cascade import run_cascade
    G = make_line_graph(10)
    affected = run_cascade(G, start_node=0, max_depth=3)
    # From node 0 with depth 3: should reach nodes 0,1,2,3
    assert set(affected["node"].to_arrow().to_pylist()).issuperset({0, 1, 2, 3})


def test_bfs_cascade_respects_depth_limit():
    from graph.cascade import run_cascade
    G = make_line_graph(20)
    affected = run_cascade(G, start_node=0, max_depth=5)
    nodes = set(affected["node"].to_arrow().to_pylist())
    # Nodes beyond depth 5 should not appear
    assert 6 not in nodes
    assert 10 not in nodes


def test_bfs_cascade_includes_distance_column():
    from graph.cascade import run_cascade
    G = make_line_graph(5)
    affected = run_cascade(G, start_node=0, max_depth=4)
    assert "distance" in affected.columns

from dataset.generator import generate_sample
from graph.builder import build_graph

def test_graph_shape():
    g=build_graph(generate_sample("NORMAL",42,0))
    assert g.x.shape==(7,16)
    assert g.edge_index.shape==(2,12)

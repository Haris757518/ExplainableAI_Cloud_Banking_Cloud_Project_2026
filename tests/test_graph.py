from dataset.generator import generate_sample
from graph.builder import build_graph

def test_graph_shape():
    g=build_graph(generate_sample("NORMAL",42,0,tx_type="UPI_PAYMENT"))
    assert g.x.shape==(5,20)
    assert g.edge_index.shape==(2,8)
    assert g.edge_weight.shape==(8,)

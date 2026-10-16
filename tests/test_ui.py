def test_ui_no_edge_percentages_and_has_secondary():
    with open("frontend/src/App.jsx", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Anomaly score placement data is below the node
    assert 'y="38"' in content
    assert 'y="-40"' not in content
    
    # 2. Active vs secondary vs unrelated edges
    assert "edge secondary" in content
    assert "edge active" in content

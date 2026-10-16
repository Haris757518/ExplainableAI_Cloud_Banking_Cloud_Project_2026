from dataset.generator import generate_sample, TX_TYPES

SCENARIOS=["NORMAL","CPU_SPIKE","DATABASE_LATENCY","SERVICE_OVERLOAD","NETWORK_DEGRADATION","CASCADING_FAILURE"]

def test_all_scenarios_generate():
    for i, scenario in enumerate(SCENARIOS):
        s=generate_sample(scenario, seed=123, index=i, tx_type=TX_TYPES[i%len(TX_TYPES)])
        assert len(s.nodes)>=5
        assert len(s.edges)>=4
        assert len(s.telemetry)==len(s.nodes)
        assert s.scenario==scenario
        assert s.transaction.path

def test_reproducibility():
    a=generate_sample("DATABASE_LATENCY",42,7,tx_type="UPI_PAYMENT").model_dump(mode="json")
    b=generate_sample("DATABASE_LATENCY",42,7,tx_type="UPI_PAYMENT").model_dump(mode="json")
    assert a==b

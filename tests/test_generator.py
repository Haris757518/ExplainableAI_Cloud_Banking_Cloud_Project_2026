from dataset.generator import generate_sample

SCENARIOS=["NORMAL","CPU_SPIKE","DATABASE_LATENCY","SERVICE_OVERLOAD","NETWORK_DEGRADATION","CASCADING_FAILURE"]

def test_all_scenarios_generate():
    for i, scenario in enumerate(SCENARIOS):
        s=generate_sample(scenario, seed=123, index=i)
        assert len(s.nodes)==7
        assert len(s.edges)==6
        assert len(s.telemetry)==7
        assert s.scenario==scenario

def test_reproducibility():
    a=generate_sample("DATABASE_LATENCY",42,7).model_dump(mode="json")
    b=generate_sample("DATABASE_LATENCY",42,7).model_dump(mode="json")
    assert a==b

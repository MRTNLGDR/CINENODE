from __future__ import annotations

import pytest

from cinenode.schemas import WorkflowGraph
from cinenode.workflow import WorkflowError, topological_order, validate_graph


def graph(nodes, edges):
    return WorkflowGraph.model_validate({"version": 1, "nodes": nodes, "edges": edges, "metadata": {}})


def test_valid_graph_has_stable_topological_order():
    value = graph(
        [
            {"id": "a", "type": "input.number", "params": {"value": 2}},
            {"id": "b", "type": "input.number", "params": {"value": 3}},
            {"id": "sum", "type": "math.add", "params": {}},
            {"id": "out", "type": "output.json", "params": {}},
        ],
        [
            {"id": "e1", "source": "a", "source_port": "value", "target": "sum", "target_port": "a"},
            {"id": "e2", "source": "b", "source_port": "value", "target": "sum", "target_port": "b"},
            {"id": "e3", "source": "sum", "source_port": "value", "target": "out", "target_port": "value"},
        ],
    )
    assert validate_graph(value) == []
    order = topological_order(value)
    assert order.index("a") < order.index("sum")
    assert order.index("b") < order.index("sum")
    assert order.index("sum") < order.index("out")


def test_cycle_is_rejected():
    value = graph(
        [
            {"id": "a", "type": "text.concat", "params": {}},
            {"id": "b", "type": "text.concat", "params": {}},
        ],
        [
            {"id": "e1", "source": "a", "source_port": "text", "target": "b", "target_port": "a"},
            {"id": "e2", "source": "b", "source_port": "text", "target": "a", "target_port": "a"},
        ],
    )
    assert "O workflow contém ciclo" in validate_graph(value)
    with pytest.raises(WorkflowError) as caught:
        topological_order(value)
    assert caught.value.code == "INVALID_GRAPH"


def test_duplicate_target_port_is_rejected():
    value = graph(
        [
            {"id": "a", "type": "input.text", "params": {}},
            {"id": "b", "type": "input.text", "params": {}},
            {"id": "out", "type": "output.text", "params": {}},
        ],
        [
            {"id": "e1", "source": "a", "source_port": "value", "target": "out", "target_port": "value"},
            {"id": "e2", "source": "b", "source_port": "value", "target": "out", "target_port": "value"},
        ],
    )
    assert any("Mais de uma conexão" in item for item in validate_graph(value))

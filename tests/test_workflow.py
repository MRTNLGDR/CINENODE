import pytest

from cinenode.nodes import builtin_registry
from cinenode.workflow import compile_workflow, node_cache_key, resolve_inputs


def test_compile_and_resolve():
    definition={"nodes":[{"id":"a","type":"input.text","params":{"text":"hello"}},{"id":"b","type":"transform.template","inputs":{"input":{"node":"a"}},"params":{"template":"{input}!"}}]}
    compiled=compile_workflow(definition,builtin_registry()); assert compiled.order==("a","b")
    assert resolve_inputs(compiled.nodes["b"],{"a":"hello"},{})=={"input":"hello"}
    assert node_cache_key(compiled.nodes["b"],{"input":"hello"})==node_cache_key(compiled.nodes["b"],{"input":"hello"})


def test_cycle_and_missing_node_rejected():
    registry=builtin_registry()
    with pytest.raises(ValueError,match="cycle"):
        compile_workflow({"nodes":[{"id":"a","type":"input.text","inputs":{"x":{"node":"b"}}},{"id":"b","type":"input.text","inputs":{"x":{"node":"a"}}}]},registry)
    with pytest.raises(ValueError,match="missing"):
        compile_workflow({"nodes":[{"id":"a","type":"input.text","inputs":{"x":{"node":"z"}}}]},registry)

from patternloop.compiler import compile_from_traces
from patternloop.inference import MockBackend


def test_compiler_from_traces() -> None:
    backend = MockBackend(
        replies=[
            '{"name": "demo", "goal_template": "{goal}", '
            '"system_prompt": "s", "planner_prompt": "p", "evaluator_prompt": "e", '
            '"tools": [{"name": "read_file", "enabled": true}], '
            '"success": {"kind": "keywords", "keywords": [], "min_output_chars": 1}}'
        ]
    )
    spec = compile_from_traces(
        backend=backend,
        name="demo",
        goal="do thing",
        traces=["example run 1", "example run 2"],
    )
    assert spec.name == "demo"
    assert "{goal}" in spec.goal_template

"""Terminal logging for live LangGraph node execution."""

from time import perf_counter


_START_NODE = "__start__"
_END_NODE = "__end__"


def _log(label, status, message):
    prefix = f"[LangGraph: {label}]" if label else "[LangGraph]"
    print(f"{prefix} {status}: {message}", flush=True)


def _connected_nodes(graph, source):
    graph_view = graph.get_graph()
    return [
        edge.target
        for edge in graph_view.edges
        if edge.source == source
        and edge.target not in (_START_NODE, _END_NODE)
        and edge.target in graph_view.nodes
    ]


def run_with_node_tracking(graph, input_state, label=None):
    """Stream a graph's debug events, log node lifecycle, and return its state."""
    state = dict(input_state)
    active_tasks = {}
    event_error = None

    for node in _connected_nodes(graph, _START_NODE):
        _log(label, "Pending", node)

    try:
        for event in graph.stream(input_state, stream_mode="debug"):
            payload = event.get("payload", {})
            event_type = event.get("type")
            task_id = payload.get("id")
            node_name = payload.get("name", "unknown")

            if event_type == "task":
                active_tasks[task_id] = (node_name, perf_counter())
                _log(label, "Running", node_name)
            elif event_type == "task_result":
                task = active_tasks.pop(task_id, None)
                started_at = task[1] if task else perf_counter()
                elapsed = perf_counter() - started_at
                error = payload.get("error")

                if error is not None:
                    event_error = f"{node_name}: {error}"
                    _log(label, "ERROR", f"{node_name} failed after {elapsed:.3f}s: {error}")
                    continue

                result = payload.get("result")
                if isinstance(result, dict):
                    state.update(result)

                _log(label, "Completed", f"{node_name} ({elapsed:.3f}s)")
                for next_node in _connected_nodes(graph, node_name):
                    _log(label, "Pending", next_node)
    except Exception as error:
        for node_name, started_at in active_tasks.values():
            elapsed = perf_counter() - started_at
            _log(label, "ERROR", f"{node_name} failed after {elapsed:.3f}s: {error}")
        if not active_tasks:
            _log(label, "ERROR", str(error))
        raise

    if event_error is not None:
        raise RuntimeError(f"LangGraph node failed: {event_error}")

    return state
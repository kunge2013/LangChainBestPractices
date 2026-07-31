## checkpointer:检查点管理器，存储
##checkpoint:检查点，状态图的总体状态快照
## thread id 管理
##作用:记忆管理、时间旅行(time travel)、pause(human-in-the-loop)，容错
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver  # checkPointer
#
from langchain_core.runnables import RunnableConfig
from typing import Annotated
from typing_extensions import TypedDict
from operator import add


class State(TypedDict):
    foo: str  # 只会有一个
    bar: Annotated[list[str], add]  # 新的状态+ 旧的  集合变多


def node_a(state: State):
    return {"foo": "a", "bar": ["a"]}


def node_b(state: State):
    return {"foo": "b", "bar": ["b"]}


# 构建状态图
workflow = StateGraph(State)
workflow.add_node(node_a)
workflow.add_node(node_b)
workflow.add_edge(START, "node_a")
workflow.add_edge("node_a", "node_b")
workflow.add_edge("node_b", END)

# 检查点管理器
checkpointer = InMemorySaver()

# 编译
graph = workflow.compile(checkpointer=checkpointer)

# 配置
config: RunnableConfig = {
    "configurable": {"thread_id": "1"}
}

# 运行
results = graph.invoke({"foo": "", "bar": ["init"]}, config)
print(results)

# 打印状态
print(graph.get_state(config=config))

# StateSnapshot(values={'foo': 'b', 'bar': ['init', 'a', 'b']}, next=(),
# config={'configurable': {'thread_id': '1', 'checkpoint_ns': '',
# 'checkpoint_id': '1f18caf5-ea79-6adf-8002-6952f6c584d5'}},
# metadata={'source': 'loop', 'step': 2, 'parents': {}},
# created_at='2026-07-31T07:13:46.040393+00:00',
# parent_config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1f18caf5-ea74-6cd4-8001-a58ea2c5ef77'}}, tasks=(), interrupts=())
i = 0
for checkpointer_tuple in checkpointer.list(config=config):
    i = i+1
    # print(f'快照次数 = {i}')
    print()
    print(checkpointer_tuple[2]["step"])
    print(checkpointer_tuple[2]["source"])
    print(checkpointer_tuple[1]["channel_values"])

    # CheckpointTuple(config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1f18cafc-b974-6343-8002-5a794732b63b'}},
    # checkpoint={'v': 4, 'ts': '2026-07-31T07:16:48.804947+00:00', 'id': '1f18cafc-b974-6343-8002-5a794732b63b', 'channel_versions': {'__start__': '00000000000000000000000000000002.0.537206790094168', 'foo': '00000000000000000000000000000004.0.7980252857599012', 'bar': '00000000000000000000000000000004.0.7980252857599012', 'branch:to:node_a': '00000000000000000000000000000003.0.7056345919163491', 'branch:to:node_b': '00000000000000000000000000000004.0.7980252857599012'},
    # 'versions_seen': {'__input__': {}, '__start__': {'__start__': '00000000000000000000000000000001.0.2529965528056971'},
    # 'node_a': {'branch:to:node_a': '00000000000000000000000000000002.0.537206790094168'},
    # 'node_b': {'branch:to:node_b': '00000000000000000000000000000003.0.7056345919163491'}}, 'updated_channels': ['bar', 'foo'], 'channel_values': {'foo': 'b', 'bar': ['init', 'a', 'b']}}, metadata={'source': 'loop', 'step': 2, 'parents': {}},
    # parent_config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1f18cafc-b971-6c49-8001-b1c36f7e2252'}}, pending_writes=[])


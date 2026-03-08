"""
End-to-end smoke test for FinBench environment.

Run from ReactAgentEnv directory:
    source .venv/bin/activate
    python scripts/test_e2e.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from finbench_env.client import FinBenchEnv


def print_obs(label: str, obs):
    """Pretty-print an observation."""
    print(f"\n{'='*60}")
    done = getattr(obs, "done", False)
    reward = getattr(obs, "reward", 0)
    print(f"[{label}] done={done} reward={reward}")
    print(f"{'='*60}")

    # MCP CallToolObservation has .result, base Observation has .metadata
    if hasattr(obs, "result") and obs.result:
        try:
            for content in obs.result.content:
                text = getattr(content, "text", str(content))
                print(text[:2000])
        except Exception:
            print(str(obs.result)[:2000])
    elif hasattr(obs, "metadata"):
        tool_result = obs.metadata.get("tool_result", "")
        if tool_result:
            print(tool_result[:2000])
        else:
            print(json.dumps(obs.metadata, indent=2, default=str)[:2000])
    else:
        print(str(obs)[:2000])


def main():
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    traces_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "traces")

    print("Starting FinBench E2E Test...")
    print(f"Data path: {data_path}")
    print(f"Traces dir: {traces_dir}")

    test_manifest = os.path.join(data_path, "tasks", "test_manifest.json")
    default_manifest = os.path.join(data_path, "tasks", "task_manifest.json")
    manifest_path = test_manifest if os.path.exists(test_manifest) else default_manifest

    env = FinBenchEnv(
        data_path=data_path,
        traces_dir=traces_dir,
        max_steps=20,
        manifest_path=manifest_path,
    )

    try:
        # 1. Reset
        obs = env.reset(episode_id="test_001")
        print_obs("RESET", obs)

        # 2. List tools
        obs = env.list_tools()
        print_obs("LIST_TOOLS", obs)

        # 3. List files
        obs = env.call_tool("list_files", path="/")
        print_obs("LIST_FILES /", obs)

        # 4. Create a notebook
        obs = env.call_tool("create_notebook", path="work/analysis.ipynb")
        print_obs("CREATE_NOTEBOOK", obs)

        # 5. Write and run a cell
        obs = env.call_tool(
            "write_and_run",
            notebook="work/analysis.ipynb",
            source="import pandas as pd\nprint('Pandas version:', pd.__version__)"
        )
        print_obs("WRITE_AND_RUN cell 1", obs)

        # 6. Write and run another cell (kernel state persists!)
        obs = env.call_tool(
            "write_and_run",
            notebook="work/analysis.ipynb",
            source="data = {'name': ['Alice', 'Bob'], 'sales': [100, 200]}\ndf = pd.DataFrame(data)\nprint(df)"
        )
        print_obs("WRITE_AND_RUN cell 2", obs)

        # 7. Check kernel state
        obs = env.call_tool("get_kernel_state")
        print_obs("KERNEL_STATE", obs)

        # 8. Write file to output
        obs = env.call_tool("write_file", path="output/report.txt", content="Sales report:\nAlice: 100\nBob: 200\nTotal: 300")
        print_obs("WRITE_FILE", obs)

        # 9. Read notebook
        obs = env.call_tool("read_notebook", path="work/analysis.ipynb")
        print_obs("READ_NOTEBOOK", obs)

        # 10. Search files
        obs = env.call_tool("search_files", query="Alice", path="/output")
        print_obs("SEARCH_FILES", obs)

        # 11. List memory
        obs = env.call_tool("list_memory")
        print_obs("LIST_MEMORY", obs)

        # 12. Save notebook to memory
        obs = env.call_tool(
            "save_to_memory",
            notebook_path="work/analysis.ipynb",
            name="basic_analysis",
            tags="pandas,example",
            description="Simple pandas analysis pattern"
        )
        print_obs("SAVE_TO_MEMORY", obs)

        # 13. Submit
        obs = env.call_tool("submit")
        print_obs("SUBMIT", obs)

        print("\n" + "=" * 60)
        print("E2E TEST COMPLETE!")
        print(f"Done: {obs.done}")
        if hasattr(obs, "reward"):
            print(f"Final reward: {obs.reward}")
        print("=" * 60)

    finally:
        env.close()


if __name__ == "__main__":
    main()


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project is a comprehensive learning resource for the **LangChain framework**, covering both **TypeScript** and **Python** SDK implementations. Each feature is implemented in **two versions** (one per language), with every module organized in its own directory.

## Environment Setup

### Python
- Use **conda** for virtual environment management
- Environment name: `LangChainBestPractices`
- Python version: `>= 3.12`
- Create environment: `conda create -n LangChainBestPractices python>=3.12`
- Activate: `conda activate LangChainBestPractices`

### Node.js / TypeScript
- Node version: `v22.18.0`
- npm version: `11.6.2`
- Use `nvm` or equivalent to manage Node version

## Project Structure

Each LangChain feature/module lives in its own directory under a language-specific folder:

```
LangChainBestPractices/
├── python/
│   └── modules/
│       └── <module_name>/
│           └── (implementation files)
├── typescript/
│   └── modules/
│       └── <module_name>/
│           └── (implementation files)
└── doc/
    ├── python/
    │   └── Deep Agents/
    │       ├── 1.Tools.md
    │       ├── 2.Backends.md
    │       ├── 3.Permissions.md
    │       ├── 4.Multimodal inputs and outputs.md
    │       ├── 5.Sandboxes.md
    │       ├── 6.Interpreters.md
    │       ├── 6.1.Dynamic subagents.md
    │       ├── 7.Event streaming.md
    │       ├── 8.Streaming.md
    │       ├── 9.Skills.md
    │       ├── 10.Memory.md
    │       ├── 11.Context engineering in Deep Agents.md
    │       ├── 12.Profiles.md
    │       ├── 13.Subagents.md
    │       ├── 14.Async subagents.md
    │       ├── 15.Human-in-the-loop.md
    │       ├── 16.Subagent streaming.md
    │       ├── 17.Todo list.md
    │       └── 19.Sandbox.md
    └── ts/
        └── Deep Agents/
            └── (mirrors python/Deep Agents/ structure)
```

Every feature has **two implementations** — one in `python/` and one in `typescript/` — allowing direct comparison between SDK versions.
The `doc/` directory mirrors this structure with corresponding documentation chapters under `doc/python/Deep Agents/` and `doc/ts/Deep Agents/`.

## Documentation Structure (Deep Agents)

The documentation chapters under `doc/` follow a consistent numbering scheme, organized as:

| Chapter | Topic                              |
| ------- | ---------------------------------- |
| 1       | Tools                              |
| 2       | Backends                           |
| 3       | Permissions                        |
| 4       | Multimodal inputs and outputs      |
| 5       | Sandboxes                          |
| 6       | Interpreters                       |
| 6.1     | Dynamic subagents                  |
| 7       | Event streaming                    |
| 8       | Streaming                          |
| 9       | Skills                             |
| 10      | Memory                             |
| 11      | Context engineering in Deep Agents |
| 12      | Profiles                           |
| 13      | Subagents                          |
| 14      | Async subagents                    |
| 15      | Human-in-the-loop                  |
| 16      | Subagent streaming                 |
| 17      | Todo list                          |
| 19      | Sandbox                            |

Each chapter exists under both `doc/python/Deep Agents/` and `doc/ts/Deep Agents/`, keeping the documentation structure in sync with the code module organization.

## Development Guidelines

- Each module is self-contained in its own directory under `python/modules/` or `typescript/modules/`
- Features are implemented in pairs: one Python, one TypeScript
- Documentation chapters under `doc/python/` and `doc/ts/` follow the same chapter numbering and naming
- Use conda environment `LangChainBestPractices` for all Python work
- Use Node `v22.18.0` and npm `11.6.2` for all TypeScript/Node work

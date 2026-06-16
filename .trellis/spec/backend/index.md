# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains guidelines for backend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Layered package layout (commands → pipeline → adapters) | Active |
| [Database Guidelines](./database-guidelines.md) | No DB; file/JSON-based persistence conventions | Active |
| [Error Handling](./error-handling.md) | VtfError hierarchy, exit codes, raise/catch boundary | Active |
| [Feishu Schema Contract](./feishu-schema-contract.md) | Schema-backed analysis guidance and emit validation | Active |
| [Quality Guidelines](./quality-guidelines.md) | ruff / mypy-strict / pytest standards, forbidden patterns | Active |
| [Logging Guidelines](./logging-guidelines.md) | stderr Logger, levels, stdout-is-data rule | Active |

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.

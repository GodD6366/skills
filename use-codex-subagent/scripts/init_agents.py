#!/usr/bin/env python3
"""Initialize Codex custom agents for the use-subagent skill.

Creates a complete subagent team under ~/.codex/agents by default:
explorer, planner, worker, verifier, reviewer, and fixer.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from string import Template


@dataclass(frozen=True)
class AgentSpec:
    name: str
    description: str
    reasoning_effort: str
    sandbox_mode: str
    nickname_candidates: tuple[str, ...]
    developer_instructions: str


AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        name="explorer",
        description="Read-only codebase explorer for locating files, tracing execution paths, and gathering evidence before planning or implementation.",
        reasoning_effort="medium",
        sandbox_mode="read-only",
        nickname_candidates=("Scout", "Trace", "Atlas"),
        developer_instructions="""Stay in exploration mode.

Use fast search and targeted file reads to map the real code path.
Return exact file paths, symbols, and line references.
Distinguish confirmed facts from hypotheses.
Summarize only the evidence needed for the parent agent to decide the next step.

Prefer:
- locating entry points, owners, call chains, config sources, and impact radius
- concise snippets or line references instead of full-file dumps
- read-heavy work that can be summarized cleanly

Do not:
- modify files or generate patches
- propose broad fixes unless the parent agent asks
- expand into unrelated areas or repeat work already assigned elsewhere

If the implementation path is clear, say so.
If the remaining question is architectural, ambiguous, or risk-heavy, recommend planner.
""",
    ),
    AgentSpec(
        name="planner",
        description="Read-only reasoning agent for root-cause analysis, solution design, and implementation planning once the relevant evidence is known.",
        reasoning_effort="xhigh",
        sandbox_mode="read-only",
        nickname_candidates=("Helm", "Northstar", "Sage"),
        developer_instructions="""Work from evidence, not broad repository exploration.

Use the parent agent's supplied context to:
- identify the root cause
- compare the smallest viable fixes
- choose the safest implementation path
- define validation and rollback considerations

Optimize for minimal, defensible changes.
Call out assumptions, compatibility risks, and unknowns.
When more code discovery is needed, ask for a narrow explorer follow-up instead of searching broadly yourself.

Do not:
- do large mechanical searches
- implement patches unless the parent agent explicitly asks
- recommend multi-file rewrites when a smaller fix is sufficient

Return:
- root cause
- recommended fix
- affected files or modules
- key risks
- validation plan

If the path is clear, hand off to the parent agent for implementation.
""",
    ),
    AgentSpec(
        name="worker",
        description="Implementation-focused agent for clearly scoped code changes once the plan and ownership boundaries are clear.",
        reasoning_effort="medium",
        sandbox_mode="workspace-write",
        nickname_candidates=("Patch", "Forge", "Bolt"),
        developer_instructions="""Own implementation only after the target behavior, files, and boundaries are clear.

Make the smallest coherent change that solves the assigned task.
Stay within the assigned files or responsibility boundary.
Preserve existing behavior outside the requested scope.
Validate the changed behavior with the narrowest useful checks.

You are not alone in the codebase:
- do not revert edits you did not make
- adapt to concurrent changes when possible
- stop and report if another change creates a real conflict

Do not:
- redesign architecture without explicit instruction
- expand scope into unrelated cleanup
- invent new abstractions unless they are required to complete the fix

Report:
- modified files
- behavior changed
- validation performed
- remaining risks or gaps
""",
    ),
    AgentSpec(
        name="verifier",
        description="Read-only verification agent for running checks, reproducing issues, and validating behavior without expanding scope.",
        reasoning_effort="medium",
        sandbox_mode="read-only",
        nickname_candidates=("Check", "Probe", "Gauge"),
        developer_instructions="""Verify the assigned behavior, command, or risk area.

Prefer real tests, builds, typechecks, logs, browser checks, or API checks over trusting summaries.
Keep the scope narrow and report the exact command or inspection performed.

Do not:
- change production code
- broaden the task into implementation
- mask failures or omit relevant output

If verification fails, include:
- failing command or check
- key output
- suspected cause if evidence supports it
- whether a targeted fixer should be used

Return PASS, FAIL, or INCONCLUSIVE with concise evidence.
""",
    ),
    AgentSpec(
        name="reviewer",
        description="Read-only review agent for checking requirement fit, code quality, regression risk, and test coverage.",
        reasoning_effort="xhigh",
        sandbox_mode="read-only",
        nickname_candidates=("Lens", "Guard", "Critic"),
        developer_instructions="""Review the implementation against the user request and repository conventions.

Look for:
- missing requirements
- incorrect behavior
- unnecessary scope expansion
- maintainability issues
- regression risks
- weak or missing tests
- security or compatibility concerns

Do not nitpick style unless it affects correctness, maintainability, or local conventions.
Do not modify files.

Return:
- verdict: APPROVED or REQUEST_CHANGES
- findings ordered by severity
- exact files and line references when possible
- tests that should still be run
""",
    ),
    AgentSpec(
        name="fixer",
        description="Targeted implementation agent for fixing one failing check or one concrete review finding within a narrow scope.",
        reasoning_effort="medium",
        sandbox_mode="workspace-write",
        nickname_candidates=("Mend", "Patch", "Triage"),
        developer_instructions="""Fix exactly one assigned failure or review finding.

Use the provided failure output, review finding, or parent-agent instructions as the boundary.
Make the smallest safe change and preserve all unrelated work.
Run the failing check again when possible.

Do not:
- redesign the solution
- fix unrelated issues
- touch files outside the assigned scope unless explicitly necessary and reported

Report:
- status
- changed files
- what changed
- verification result
- remaining risk
""",
    ),
)

TOML_TEMPLATE = Template('''name = "$name"
description = "$description"
model = "$model"
model_reasoning_effort = "$reasoning_effort"
sandbox_mode = "$sandbox_mode"
nickname_candidates = [$nickname_candidates]
developer_instructions = """
$developer_instructions"""
''')


def toml_escape(value: str) -> str:
    return value.replace('\\', '\\\\').replace('"', '\\"')


def render_agent(spec: AgentSpec, model: str) -> str:
    nicknames = ", ".join(f'"{toml_escape(n)}"' for n in spec.nickname_candidates)
    return TOML_TEMPLATE.substitute(
        name=toml_escape(spec.name),
        description=toml_escape(spec.description),
        model=toml_escape(model),
        reasoning_effort=toml_escape(spec.reasoning_effort),
        sandbox_mode=toml_escape(spec.sandbox_mode),
        nickname_candidates=nicknames,
        developer_instructions=spec.developer_instructions.rstrip() + "\n",
    )


def prompt_model(agent_name: str) -> str:
    while True:
        value = input(f"Model ID for {agent_name}: ").strip()
        if value:
            return value
        print("Model ID cannot be empty.", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize ~/.codex/agents/*.toml for the use-subagent skill."
    )
    parser.add_argument(
        "--target-dir",
        default="~/.codex/agents",
        help="Directory where agent TOML files will be written. Default: ~/.codex/agents",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Back up and overwrite existing agent files. By default existing files are skipped.",
    )
    for spec in AGENTS:
        parser.add_argument(
            f"--{spec.name}-model",
            dest=f"{spec.name}_model",
            help=f"Model ID for {spec.name}. If omitted, prompt interactively.",
        )
    return parser.parse_args()


def backup_existing(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_name(f"{path.name}.bak.{timestamp}")
    counter = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.bak.{timestamp}.{counter}")
        counter += 1
    shutil.copy2(path, backup)
    return backup


def main() -> int:
    args = parse_args()
    target_dir = Path(os.path.expanduser(args.target_dir)).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    skipped: list[Path] = []
    overwritten: list[Path] = []
    backups: list[Path] = []

    for spec in AGENTS:
        path = target_dir / f"{spec.name}.toml"
        if path.exists() and not args.force:
            skipped.append(path)
            continue

        model = getattr(args, f"{spec.name}_model") or prompt_model(spec.name)
        content = render_agent(spec, model)

        if path.exists() and args.force:
            backups.append(backup_existing(path))
            overwritten.append(path)
        else:
            created.append(path)

        path.write_text(content, encoding="utf-8")

    if created:
        print("Created:")
        for path in created:
            print(f"  {path}")
    if overwritten:
        print("Overwritten:")
        for path in overwritten:
            print(f"  {path}")
    if backups:
        print("Backups:")
        for path in backups:
            print(f"  {path}")
    if skipped:
        print("Skipped existing files (use --force to overwrite):")
        for path in skipped:
            print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

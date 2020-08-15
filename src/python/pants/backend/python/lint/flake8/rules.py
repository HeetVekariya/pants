# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from dataclasses import dataclass
from typing import Optional, Tuple

from pants.backend.python.lint.flake8.subsystem import Flake8
from pants.backend.python.rules import pex
from pants.backend.python.rules.pex import (
    Pex,
    PexInterpreterConstraints,
    PexProcess,
    PexRequest,
    PexRequirements,
)
from pants.backend.python.target_types import PythonInterpreterCompatibility, PythonSources
from pants.core.goals.lint import LintReport, LintRequest, LintResult, LintResults, LintSubsystem
from pants.core.util_rules import source_files, stripped_source_files
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.fs import Digest, DigestSubset, GlobMatchErrorBehavior, MergeDigests, PathGlobs
from pants.engine.process import FallibleProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import FieldSet
from pants.engine.unions import UnionRule
from pants.python.python_setup import PythonSetup
from pants.util.strutil import pluralize


@dataclass(frozen=True)
class Flake8FieldSet(FieldSet):
    required_fields = (PythonSources,)

    sources: PythonSources
    compatibility: PythonInterpreterCompatibility


class Flake8Request(LintRequest):
    field_set_type = Flake8FieldSet


@dataclass(frozen=True)
class Flake8Partition:
    field_sets: Tuple[Flake8FieldSet, ...]
    interpreter_constraints: PexInterpreterConstraints


def generate_args(
    *, source_files: SourceFiles, flake8: Flake8, report_file_name: Optional[str]
) -> Tuple[str, ...]:
    args = []
    if flake8.config:
        args.append(f"--config={flake8.config}")
    if report_file_name:
        args.append(f"--output-file={report_file_name}")
    args.extend(flake8.args)
    args.extend(source_files.files)
    return tuple(args)


@rule
async def flake8_lint_partition(
    partition: Flake8Partition, flake8: Flake8, lint_subsystem: LintSubsystem
) -> LintResult:
    requirements_pex_request = Get(
        Pex,
        PexRequest(
            output_filename="flake8.pex",
            internal_only=True,
            requirements=PexRequirements(flake8.all_requirements),
            interpreter_constraints=(
                partition.interpreter_constraints
                or PexInterpreterConstraints(flake8.interpreter_constraints)
            ),
            entry_point=flake8.entry_point,
        ),
    )

    config_digest_request = Get(
        Digest,
        PathGlobs(
            globs=[flake8.config] if flake8.config else [],
            glob_match_error_behavior=GlobMatchErrorBehavior.error,
            description_of_origin="the option `--flake8-config`",
        ),
    )

    source_files_request = Get(
        SourceFiles, SourceFilesRequest(field_set.sources for field_set in partition.field_sets)
    )

    requirements_pex, config_digest, source_files = await MultiGet(
        requirements_pex_request, config_digest_request, source_files_request
    )

    input_digest = await Get(
        Digest,
        MergeDigests((source_files.snapshot.digest, requirements_pex.digest, config_digest)),
    )

    address_references = ", ".join(
        sorted(field_set.address.spec for field_set in partition.field_sets)
    )
    report_file_name = "flake8_report.txt" if lint_subsystem.reports_dir else None

    result = await Get(
        FallibleProcessResult,
        PexProcess(
            requirements_pex,
            argv=generate_args(
                source_files=source_files, flake8=flake8, report_file_name=report_file_name,
            ),
            input_digest=input_digest,
            output_files=(report_file_name,) if report_file_name else None,
            description=(
                f"Run Flake8 on {pluralize(len(partition.field_sets), 'target')}: "
                f"{address_references}"
            ),
        ),
    )

    report = None
    if report_file_name:
        report_digest = await Get(
            Digest,
            DigestSubset(
                result.output_digest,
                PathGlobs(
                    [report_file_name],
                    glob_match_error_behavior=GlobMatchErrorBehavior.warn,
                    description_of_origin="Flake8 report file",
                ),
            ),
        )
        report = LintReport(report_file_name, report_digest)

    return LintResult.from_fallible_process_result(result, linter_name="Flake8", report=report)


@rule(desc="Lint using Flake8")
async def flake8_lint(
    request: Flake8Request, flake8: Flake8, python_setup: PythonSetup
) -> LintResults:
    if flake8.skip:
        return LintResults()

    # NB: Flake8 output depends upon which Python interpreter version it's run with
    # (http://flake8.pycqa.org/en/latest/user/invocation.html). We batch targets by their
    # constraints to ensure, for example, that all Python 2 targets run together and all Python 3
    # targets run together.
    constraints_to_field_sets = PexInterpreterConstraints.group_field_sets_by_constraints(
        request.field_sets, python_setup
    )
    partitioned_results = await MultiGet(
        Get(LintResult, Flake8Partition(partition_field_sets, partition_compatibility))
        for partition_compatibility, partition_field_sets in constraints_to_field_sets.items()
    )
    return LintResults(partitioned_results)


def rules():
    return [
        *collect_rules(),
        UnionRule(LintRequest, Flake8Request),
        *pex.rules(),
        *source_files.rules(),
        *stripped_source_files.rules(),
    ]

"""Encodes the three-layer dependency rule for src/glab_dash.

Domain: stdlib-only. Application: domain + gateway interfaces only, never
concrete infrastructure. Infrastructure: may depend on either.
"""

import re
import sys

from archunitpython import project_files

SRC_ROOT = "src"

# archunitpython has no "stdlib" concept; "external" means "outside this
# project". Build a regex that matches anything whose top-level module name
# isn't in the stdlib, to approximate "non-stdlib" via a negative lookahead.
_NOT_STDLIB = re.compile(
    r"^(?!(" + "|".join(re.escape(name) for name in sys.stdlib_module_names) + r")(\.|$)).+$"
)


def test_domain_is_stdlib_only():
    violations = (
        project_files(SRC_ROOT)
        .in_folder("**/domain/**")
        .should_not()
        .depend_on_external_modules()
        .matching(_NOT_STDLIB)
        .check()
    )

    assert violations == []


def test_domain_does_not_depend_on_other_layers():
    violations = (
        project_files(SRC_ROOT)
        .in_folder("**/domain/**")
        .should_not()
        .depend_on_files()
        .in_folder(re.compile(r"/(application|infrastructure)(/|$)"))
        .check()
    )

    assert violations == []


def test_application_does_not_depend_on_infrastructure():
    violations = (
        project_files(SRC_ROOT)
        .in_folder("**/application/**")
        .should_not()
        .depend_on_files()
        .in_folder("**/infrastructure/**")
        .check()
    )

    assert violations == []

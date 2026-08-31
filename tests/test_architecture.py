"""Encodes the three-layer dependency rule for src/glab_dash.

Domain: stdlib-only. Application: domain + gateway interfaces only, never
concrete infrastructure. Infrastructure: may depend on either.
"""

import re
import sys

from archunitpython import assert_passes, project_files

SRC_ROOT = "src/"

# archunitpython has no "stdlib" concept; "external" means "outside this
# project". Build a regex that matches anything whose top-level module name
# isn't in the stdlib, to approximate "non-stdlib" via a negative lookahead.
_NOT_STDLIB = re.compile(
    r"^(?!(" + "|".join(re.escape(name) for name in sys.stdlib_module_names) + r")(\.|$)).+$"
)


# Workaround for an archunitpython bug: in_folder()'s glob matching operates
# on the directory path with the filename stripped, so a file living
# directly inside the target folder (e.g. domain/credentials.py) leaves no
# trailing "/" for "**/domain/**" to match against — only files nested at
# least one level deeper are ever caught. A regex anchored on a folder
# boundary (trailing "/" OR end of string) matches both cases.
_DOMAIN = re.compile(r"/domain(/|$)")
_APPLICATION = re.compile(r"/application(/|$)")
_INFRASTRUCTURE = re.compile(r"/infrastructure(/|$)")


def test_domain_is_stdlib_only() -> None:
    rule = (
        project_files(SRC_ROOT)
        .in_folder(_DOMAIN)
        .should_not()
        .depend_on_external_modules()
        .matching(_NOT_STDLIB)
    )

    assert_passes(rule)


def test_domain_does_not_depend_on_other_layers() -> None:
    rule = (
        project_files(SRC_ROOT)
        .in_folder(_DOMAIN)
        .should_not()
        .depend_on_files()
        .in_folder(re.compile(r"/(application|infrastructure)(/|$)"))
    )

    assert_passes(rule)


def test_application_does_not_depend_on_infrastructure() -> None:
    rule = (
        project_files(SRC_ROOT)
        .in_folder(_APPLICATION)
        .should_not()
        .depend_on_files()
        .in_folder(_INFRASTRUCTURE)
    )

    assert_passes(rule)

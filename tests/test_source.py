"""Structural tests on the source and the tooling around it.

These turn README claims into checks: the executable file is pure
Brainfuck, it is reproducibly generated, it reads at most nine bytes, it can
only ever print the eight answers; nothing in the toolchain can reach a
network, a clock or the application's answers.
"""

from __future__ import annotations

import ast
import unittest

from tests.support import ANNOTATED_PATH, PROGRAM_PATH, ROOT, source
from tools import interpreter as bf
from tools import program, strip

TOOLS = ROOT / "tools"
TERMINATED_LENGTH = len("YYYYMMDD\n")
SUPPORTED_DATE_COUNT = 73049

# Modules that could reach outside the process or read the clock.
FORBIDDEN_EVERYWHERE = {
    "socket",
    "ssl",
    "http",
    "urllib",
    "ftplib",
    "smtplib",
    "subprocess",
    "multiprocessing",
    "ctypes",
    "asyncio",
}
# The generator and assembler must not know about dates at all.
FORBIDDEN_IN_GENERATOR = FORBIDDEN_EVERYWHERE | {
    "datetime",
    "calendar",
    "time",
    "random",
}
GENERATOR_MODULES = ("bfasm.py", "program.py", "strip.py", "build.py")
INTERPRETER_MODULES = ("interpreter.py", "fastbf.py")
INTERPRETER_ALLOWED = {"__future__", "sys", "dataclasses", "tools.interpreter"}


def imported_modules(path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def top_level(names: set[str]) -> set[str]:
    return {name.split(".")[0] for name in names}


class PurityTests(unittest.TestCase):
    def test_executable_holds_only_commands_and_line_feeds(self):
        allowed = set(bf.COMMANDS) | {"\n"}
        self.assertLessEqual(set(source()), allowed)

    def test_brackets_balance(self):
        bf.match_brackets(bf.instructions(source()))

    def test_comments_in_the_annotated_source_hold_no_commands(self):
        for number, text in enumerate(ANNOTATED_PATH.read_text().splitlines(), 1):
            if set(text.strip()) - set(bf.COMMANDS):
                with self.subTest(line=number):
                    self.assertFalse(set(text) & set(bf.COMMANDS), text)


class ReproducibilityTests(unittest.TestCase):
    def test_annotated_source_is_what_the_generator_produces(self):
        text, _ = program.build()
        self.assertEqual(ANNOTATED_PATH.read_text(encoding="ascii"), text)

    def test_executable_is_the_stripped_annotated_source(self):
        annotated = ANNOTATED_PATH.read_text(encoding="ascii")
        self.assertEqual(
            PROGRAM_PATH.read_text(encoding="ascii"), strip.strip(annotated)
        )

    def test_generator_is_deterministic(self):
        self.assertEqual(program.build()[0], program.build()[0])


class ShapeTests(unittest.TestCase):
    def test_at_most_nine_reads(self):
        self.assertEqual(bf.instructions(source()).count(","), TERMINATED_LENGTH)

    def test_output_instructions_spell_only_the_eight_answers(self):
        names = (*program.WEEKDAY_NAMES, program.INVALID_TEXT, program.NEWLINE)
        expected = sum(len(name) for name in names)
        self.assertEqual(bf.instructions(source()).count("."), expected)

    def test_program_is_smaller_than_the_set_of_dates(self):
        # A weak bound, stated as such in TESTING.md: a per date table would
        # need at least one instruction per date.
        self.assertLess(len(bf.instructions(source())), SUPPORTED_DATE_COUNT)


class ToolingBoundaryTests(unittest.TestCase):
    def test_no_tool_can_reach_a_network_or_spawn_a_process(self):
        for path in sorted(TOOLS.glob("*.py")):
            with self.subTest(module=path.name):
                found = top_level(imported_modules(path)) & FORBIDDEN_EVERYWHERE
                self.assertEqual(found, set())

    def test_generator_knows_nothing_about_dates(self):
        for name in GENERATOR_MODULES:
            with self.subTest(module=name):
                found = (
                    top_level(imported_modules(TOOLS / name)) & FORBIDDEN_IN_GENERATOR
                )
                self.assertEqual(found, set())

    def test_interpreters_import_only_what_they_need(self):
        for name in INTERPRETER_MODULES:
            with self.subTest(module=name):
                self.assertLessEqual(
                    imported_modules(TOOLS / name), INTERPRETER_ALLOWED
                )

    def test_interpreters_hold_no_application_knowledge(self):
        words = ("MONDAY", "INVALID", "leap", "weekday", "fuckwhatday.bf", "calendar")
        for name in INTERPRETER_MODULES:
            text = (TOOLS / name).read_text(encoding="utf-8")
            code = "\n".join(
                line for line in text.splitlines() if not line.lstrip().startswith("#")
            )
            docstring = ast.get_docstring(ast.parse(text), clean=False) or ""
            self.assertIn(docstring, code)
            code = code.replace(docstring, "")
            for word in words:
                with self.subTest(module=name, word=word):
                    self.assertNotIn(word, code)


if __name__ == "__main__":
    unittest.main()

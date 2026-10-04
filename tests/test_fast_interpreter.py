"""The fast interpreter must agree with the boring one exactly.

The exhaustive calendar test runs on the fast interpreter, so its evidence is
only as good as this agreement. Agreement is checked on hand written
programs and on a seeded corpus of random programs, comparing output, final
tape, pointer and instruction count.
"""

from __future__ import annotations

import random
import unittest

from tools import fastbf
from tools import interpreter as bf

RANDOM_SEED = 20261004
RANDOM_PROGRAMS = 3000
RANDOM_MAX_LENGTH = 40
RANDOM_INPUT_LENGTH = 4
RANDOM_STEP_LIMIT = 5000
RANDOM_TAPE_LENGTH = 16
BODY_ALPHABET = "+-<>.,"
OPEN_WEIGHT = 0.12
CLOSE_WEIGHT = 0.15

HAND_WRITTEN = (
    "++++++[>+++++++<-]>.",
    "+++[>++[>+++<-]<-]>>.",
    "-.",
    "+[-]+[+]",
    ",[.,]",
    "++[->+++>-<<]>.>.",
    "+++++[->>+<<]>>[-<+>]<.",
    ">+<+[>[-]<-]>.",
    ",>,<[->+<]>.",
    # Found by the random corpus: the body visits cell -1 without changing it.
    "+..[<>-]",
)


def _random_program(rng: random.Random) -> str:
    chars: list[str] = []
    depth = 0
    for _ in range(rng.randint(1, RANDOM_MAX_LENGTH)):
        roll = rng.random()
        if roll < OPEN_WEIGHT:
            chars.append("[")
            depth += 1
        elif roll < OPEN_WEIGHT + CLOSE_WEIGHT and depth:
            chars.append("]")
            depth -= 1
        else:
            chars.append(rng.choice(BODY_ALPHABET))
    return "".join(chars) + "]" * depth


def _outcome(module_run, source, data, **options):
    try:
        return module_run(source, data, **options)
    except bf.BrainfuckError as error:
        return error


class AgreementTests(unittest.TestCase):
    def assert_agree(self, source, data=b"", **options):
        slow = _outcome(bf.run, source, data, **options)
        fast = _outcome(fastbf.run, source, data, **options)
        if isinstance(slow, bf.TapeBoundsError):
            self.assertIsInstance(fast, bf.TapeBoundsError, source)
        elif isinstance(slow, bf.BrainfuckError):
            # The fast interpreter checks limits at segment and loop
            # boundaries, so it may name a different failure; it must fail.
            self.assertIsInstance(fast, bf.BrainfuckError, source)
        else:
            self.assertEqual(slow, fast, source)

    def test_hand_written_programs(self):
        for source in HAND_WRITTEN:
            for eof in bf.EOF_MODES:
                with self.subTest(source=source, eof=eof):
                    self.assert_agree(source, b"\x03\x05", eof=eof)

    def test_random_programs(self):
        rng = random.Random(RANDOM_SEED)
        for _ in range(RANDOM_PROGRAMS):
            source = _random_program(rng)
            data = bytes(
                rng.randrange(bf.CELL_MODULUS) for _ in range(RANDOM_INPUT_LENGTH)
            )
            eof = rng.choice(bf.EOF_MODES)
            with self.subTest(source=source, eof=eof):
                self.assert_agree(
                    source,
                    data,
                    eof=eof,
                    step_limit=RANDOM_STEP_LIMIT,
                    tape_length=RANDOM_TAPE_LENGTH,
                )

    def test_random_corpus_finishes_often_enough_to_mean_something(self):
        rng = random.Random(RANDOM_SEED)
        finished = 0
        for _ in range(RANDOM_PROGRAMS):
            source = _random_program(rng)
            data = bytes(
                rng.randrange(bf.CELL_MODULUS) for _ in range(RANDOM_INPUT_LENGTH)
            )
            rng.choice(bf.EOF_MODES)
            outcome = _outcome(
                bf.run,
                source,
                data,
                step_limit=RANDOM_STEP_LIMIT,
                tape_length=RANDOM_TAPE_LENGTH,
            )
            finished += not isinstance(outcome, bf.BrainfuckError)
        self.assertGreater(finished, RANDOM_PROGRAMS // 4)


class FastFailureTests(unittest.TestCase):
    def test_infinite_loop_hits_the_step_limit(self):
        with self.assertRaises(bf.StepLimitExceeded):
            fastbf.run("+[]", step_limit=1000)

    def test_unmatched_brackets_are_rejected(self):
        with self.assertRaises(bf.BracketError):
            fastbf.run("[")

    def test_unknown_eof_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            fastbf.run("", eof="sideways")

    def test_compiled_program_is_reusable(self):
        program = fastbf.Program(",.")
        self.assertEqual(program.run(b"a").output, b"a")
        self.assertEqual(program.run(b"b").output, b"b")


if __name__ == "__main__":
    unittest.main()

"""Translate a Brainfuck program into equivalent C, instruction for instruction.

Like the interpreters, this contains no FuckWhatDay specific logic: it
translates any valid Brainfuck program. Each instruction becomes the C
statement that does the same thing to the same tape:

    >  p += 1              <  p -= 1
    +  *p += 1             -  *p -= 1
    .  putchar(*p)         ,  read a byte; at end of input leave *p unchanged
    [  while (*p) {        ]  }

The only liberty taken is folding a run of the same instruction into one
statement (``+++`` becomes ``*p += 3``), which C's wrapping of unsigned
char arithmetic makes exact. Cells are ``unsigned char``, so they wrap
modulo 256 as the execution model requires.

The translated program does not check tape bounds; the interpreters do.
Standard input and output are switched to binary mode on Windows so bytes
pass through unaltered, exactly as the interpreters see them.
"""

from __future__ import annotations

from tools.interpreter import DEFAULT_TAPE_LENGTH, instructions, match_brackets

_INDENT = "    "
_FOLDABLE = {
    ">": "p += {n};",
    "<": "p -= {n};",
    "+": "*p += {n};",
    "-": "*p -= {n};",
}
_SINGLE = {
    ".": "putchar(*p);",
    ",": "c = getchar(); if (c != EOF) *p = (unsigned char)c;",
}

_PROLOGUE = f"""\
/* Translated from Brainfuck by tools/bf2c.py; do not edit. */
#include <stdio.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

static unsigned char tape[{DEFAULT_TAPE_LENGTH}];

int main(void)
{{
    unsigned char *p = tape;
    int c;
#ifdef _WIN32
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    (void)c;
"""

_EPILOGUE = """\
    fflush(stdout);
    return 0;
}
"""


def translate(source: str) -> str:
    """Return a complete C program equivalent to the Brainfuck ``source``."""
    code = instructions(source)
    match_brackets(code)
    lines: list[str] = []
    depth = 1
    index = 0
    while index < len(code):
        op = code[index]
        if op in _FOLDABLE:
            run = index
            while run < len(code) and code[run] == op:
                run += 1
            lines.append(_INDENT * depth + _FOLDABLE[op].format(n=run - index))
            index = run
            continue
        if op == "[":
            lines.append(_INDENT * depth + "while (*p) {")
            depth += 1
        elif op == "]":
            depth -= 1
            lines.append(_INDENT * depth + "}")
        else:
            lines.append(_INDENT * depth + _SINGLE[op])
        index += 1
    return _PROLOGUE + "\n".join(lines) + "\n" + _EPILOGUE

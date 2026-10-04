/*
 * A small Brainfuck interpreter for the browser.
 *
 * Same execution model as tools/interpreter.py: byte cells wrapping modulo
 * 256, a fixed tape starting at cell 0, end of input leaves the cell
 * unchanged, an instruction limit. It contains no knowledge of any
 * particular program; tests/test_site.py holds it to that and checks its
 * answers against the oracle through Node.
 */
(function (root) {
  "use strict";

  var COMMANDS = "><+-.,[]";
  var DEFAULT_TAPE_LENGTH = 30000;
  var DEFAULT_STEP_LIMIT = 50000000;

  function compile(source) {
    var code = "";
    for (var i = 0; i < source.length; i++) {
      if (COMMANDS.indexOf(source[i]) !== -1) {
        code += source[i];
      }
    }
    var jumps = new Int32Array(code.length);
    var stack = [];
    for (var j = 0; j < code.length; j++) {
      if (code[j] === "[") {
        stack.push(j);
      } else if (code[j] === "]") {
        if (stack.length === 0) {
          throw new Error("unmatched ] at instruction " + j);
        }
        var open = stack.pop();
        jumps[open] = j;
        jumps[j] = open;
      }
    }
    if (stack.length !== 0) {
      throw new Error("unmatched [ at instruction " + stack.pop());
    }
    return { code: code, jumps: jumps };
  }

  function run(program, input, options) {
    options = options || {};
    var tapeLength = options.tapeLength || DEFAULT_TAPE_LENGTH;
    var stepLimit = options.stepLimit || DEFAULT_STEP_LIMIT;
    var code = program.code;
    var jumps = program.jumps;
    var tape = new Uint8Array(tapeLength);
    var output = [];
    var pointer = 0;
    var read = 0;
    var steps = 0;
    for (var pc = 0; pc < code.length; pc++) {
      if (steps >= stepLimit) {
        throw new Error("exceeded " + stepLimit + " instructions");
      }
      steps++;
      switch (code[pc]) {
        case ">":
          if (++pointer >= tapeLength) throw new Error("pointer left the tape");
          break;
        case "<":
          if (--pointer < 0) throw new Error("pointer left the tape");
          break;
        case "+":
          tape[pointer]++;
          break;
        case "-":
          tape[pointer]--;
          break;
        case ".":
          output.push(tape[pointer]);
          break;
        case ",":
          if (read < input.length) tape[pointer] = input[read++];
          break;
        case "[":
          if (tape[pointer] === 0) pc = jumps[pc];
          break;
        case "]":
          if (tape[pointer] !== 0) pc = jumps[pc];
          break;
      }
    }
    return { output: output, tape: tape, pointer: pointer, steps: steps, consumed: read };
  }

  var api = { compile: compile, run: run, COMMANDS: COMMANDS };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.Brainfuck = api;
  }
})(this);

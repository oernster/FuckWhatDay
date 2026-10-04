/*
 * The live demo. Loads the real program (a byte for byte copy of
 * src/fuckwhatday.bf) and runs it with bf.js. Nothing here computes a
 * weekday; nothing here reads the clock. The page, like the program,
 * does not know what day it is.
 */
(function () {
  "use strict";

  var program = null;
  var tapeMap = [];
  var encoder = new TextEncoder();
  var decoder = new TextDecoder();

  function $(id) {
    return document.getElementById(id);
  }

  function formatNumber(n) {
    return n.toLocaleString("en-GB");
  }

  function count(code, ch) {
    return code.split(ch).length - 1;
  }

  function fillStats(code) {
    var stats = {
      instructions: code.length,
      reads: count(code, ","),
      writes: count(code, "."),
      loops: count(code, "[")
    };
    document.querySelectorAll("[data-stat]").forEach(function (el) {
      var value = stats[el.getAttribute("data-stat")];
      if (value !== undefined) el.textContent = formatNumber(value);
    });
  }

  function buildTapeTable() {
    var body = $("tape-body");
    body.innerHTML = "";
    tapeMap.forEach(function (cell) {
      var row = document.createElement("tr");
      row.innerHTML =
        "<td>" + cell.address + "</td>" +
        "<td><code>" + cell.name + "</code></td>" +
        "<td class=\"tape-value\" id=\"cell-" + cell.address + "\">0</td>" +
        "<td class=\"tape-role\">" + cell.role + "</td>";
      body.appendChild(row);
    });
  }

  function showTape(tape) {
    tapeMap.forEach(function (cell) {
      var el = $("cell-" + cell.address);
      el.textContent = tape[cell.address];
      el.classList.toggle("is-set", tape[cell.address] !== 0);
    });
  }

  function setResult(text, kind) {
    var el = $("demo-result");
    el.textContent = text;
    el.className = "result " + kind;
  }

  function runDate(text) {
    if (!program) return;
    var input = encoder.encode(text + "\n");
    var started = performance.now();
    var result;
    try {
      result = Brainfuck.run(program, input);
    } catch (error) {
      setResult("The interpreter refused: " + error.message, "is-invalid");
      return;
    }
    var elapsed = performance.now() - started;
    var answer = decoder.decode(new Uint8Array(result.output)).trim();
    setResult(answer, answer === "INVALID" ? "is-invalid" : "is-valid");
    $("demo-steps").textContent = formatNumber(result.steps);
    $("demo-time").textContent = elapsed.toFixed(1) + " ms";
    $("demo-consumed").textContent = result.consumed + " of " + input.length;
    $("demo-echo").textContent = JSON.stringify(text + "\n");
    showTape(result.tape);
  }

  function hasDemo() {
    return $("demo-form") !== null;
  }

  function wire() {
    if (!hasDemo()) return;
    $("demo-form").addEventListener("submit", function (event) {
      event.preventDefault();
      runDate($("demo-input").value);
    });
    document.querySelectorAll("[data-try]").forEach(function (button) {
      button.addEventListener("click", function () {
        var value = button.getAttribute("data-try");
        $("demo-input").value = value;
        runDate(value);
      });
    });
    $("demo-today").addEventListener("click", function () {
      setResult(
        "FuckWhatDay does not read the system clock. You know what day it is. Tell it.",
        "is-refusal"
      );
    });
  }

  function load() {
    Promise.all([
      fetch("fuckwhatday.bf").then(function (r) {
        if (!r.ok) throw new Error("fuckwhatday.bf: HTTP " + r.status);
        return r.text();
      }),
      fetch("tape-map.json").then(function (r) {
        if (!r.ok) throw new Error("tape-map.json: HTTP " + r.status);
        return r.json();
      })
    ])
      .then(function (loaded) {
        program = Brainfuck.compile(loaded[0]);
        tapeMap = loaded[1];
        fillStats(program.code);
        if (!hasDemo()) return;
        buildTapeTable();
        $("demo-run").disabled = false;
        setResult("Ready. Enter a date as YYYYMMDD.", "is-idle");
      })
      .catch(function (error) {
        if (!hasDemo()) return;
        setResult(
          "Could not load the program (" + error.message + "). " +
          "This page has to be served over HTTP, not opened as a file.",
          "is-invalid"
        );
      });
  }

  wire();
  load();
})();

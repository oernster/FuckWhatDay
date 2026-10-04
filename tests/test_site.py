"""The GitHub Pages site: generated, linked correctly and honest.

The site's demo runs the real program on ``docs/bf.js``. These tests hold
that interpreter to the oracle (through Node, skipped without it), hold the
site's copies of the program and tape map to the generator and check the
pages themselves: generated from the layout, every local link resolving, no
clock read anywhere.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest

from tests.support import ROOT, source
from tests.test_invalid_dates import IMPOSSIBLE, MALFORMED, OUT_OF_RANGE
from tools import build, reference, site

DOCS = ROOT / "docs"
BF_JS = DOCS / "bf.js"
SITE_JS = DOCS / "site.js"
SAMPLE_STRIDE = 211
LOCAL_LINK = re.compile(r'(?:href|src)="(?!https?:|#|mailto:)([^"]+)"')

# Run docs/bf.js on each input; read {"program": ..., "inputs": [...]} as
# JSON on stdin and print the outputs as a JSON list of strings.
NODE_RUNNER = """
const bf = require(process.argv[1]);
let raw = "";
process.stdin.on("data", c => raw += c);
process.stdin.on("end", () => {
  const job = JSON.parse(raw);
  const program = bf.compile(job.program);
  const outputs = job.inputs.map(text => {
    const input = Buffer.from(text, "latin1");
    return Buffer.from(bf.run(program, input).output).toString("latin1");
  });
  process.stdout.write(JSON.stringify(outputs));
});
"""


class GeneratedFilesTests(unittest.TestCase):
    def test_pages_are_what_the_generator_produces(self):
        for page in site.PAGES:
            with self.subTest(page=page.file):
                committed = (DOCS / page.file).read_text(encoding="utf-8")
                self.assertEqual(committed, site.render(page))

    def test_site_program_is_the_committed_program(self):
        self.assertEqual(build.SITE_PROGRAM.read_text(encoding="ascii"), source())

    def test_site_tape_map_is_the_layout(self):
        committed = build.SITE_TAPE_MAP.read_text(encoding="ascii")
        self.assertEqual(committed, build.tape_map_json())


class PageTests(unittest.TestCase):
    def test_every_local_link_resolves(self):
        for page in site.PAGES:
            text = (DOCS / page.file).read_text(encoding="utf-8")
            for target in LOCAL_LINK.findall(text):
                with self.subTest(page=page.file, target=target):
                    self.assertTrue((DOCS / target).is_file())

    def test_nothing_on_the_site_reads_the_clock(self):
        for path in (BF_JS, SITE_JS):
            with self.subTest(script=path.name):
                self.assertNotRegex(path.read_text(encoding="utf-8"), r"\bDate\b")

    def test_browser_interpreter_holds_no_application_knowledge(self):
        text = BF_JS.read_text(encoding="utf-8")
        for word in ("MONDAY", "INVALID", "leap", "weekday", "calendar"):
            with self.subTest(word=word):
                self.assertNotIn(word, text)


@unittest.skipUnless(shutil.which("node"), "node is not on PATH")
class BrowserInterpreterTests(unittest.TestCase):
    def test_browser_interpreter_matches_the_oracle(self):
        dates = list(reference.supported_dates())[::SAMPLE_STRIDE]
        inputs = [reference.encode(date) for date in dates]
        inputs += [(text + "\n").encode("ascii") for text in IMPOSSIBLE + OUT_OF_RANGE]
        inputs += list(MALFORMED)
        job = {"program": source(), "inputs": [d.decode("latin-1") for d in inputs]}
        result = subprocess.run(
            ["node", "-e", NODE_RUNNER, str(BF_JS)],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            check=True,
        )
        outputs = json.loads(result.stdout)
        for data, output in zip(inputs, outputs, strict=True):
            with self.subTest(data=data):
                expected = reference.expected_output(data).decode("ascii")
                self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main()

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const resultUrl = new URL("../app/lib/retrieval-checkup-v1.json", import.meta.url);
const suiteUrl = new URL("../../evals/retrieval-checkup-v1.json", import.meta.url);

test("retrieval checkup keeps one machine-readable result behind the design page", async () => {
  const result = JSON.parse(await readFile(resultUrl, "utf8"));
  const suite = JSON.parse(await readFile(suiteUrl, "utf8"));
  const page = await readFile(new URL("../app/design/page.tsx", import.meta.url), "utf8");

  assert.equal(result.schema_version, "retrieval-checkup-result-v1");
  assert.equal(result.status, "first_frozen_public_development_result_not_product_release_claim");
  assert.equal(result.dataset.case_count, 16);
  assert.deepEqual(result.dataset.model_split, { "CZ-R1": 8, "CZ-R2": 8 });
  assert.equal(result.dataset.document_count, 6);
  assert.equal(result.dataset.section_count, 27);
  assert.ok(result.dataset.multi_source_case_count >= 6);
  assert.ok(result.dataset.robust_expression_case_count >= 4);
  assert.equal(result.runtime_identity.provider_calls, 0);
  assert.deepEqual(result.retrievers.map((item) => item.retriever_id), ["bm25", "bge", "rrf"]);
  assert.equal(result.cases.length, 16);
  assert.deepEqual(result.cases.map((item) => item.case_id), suite.cases.map((item) => item.case_id));

  for (const summary of result.retrievers) {
    const records = result.cases.map((item) => item.retrievals[summary.retriever_id]);
    assert.equal(
      summary.full_coverage_at_5.passed_cases,
      records.filter((item) => item.full_coverage_at_5).length,
    );
    assert.equal(
      summary.full_coverage_at_10.passed_cases,
      records.filter((item) => item.full_coverage_at_10).length,
    );
    assert.equal(
      summary.wrong_model_hits_at_10,
      records.reduce((total, item) => total + item.wrong_model_hits_at_10.length, 0),
    );
    assert.equal(summary.full_coverage_at_5.total_cases, 16);
    assert.equal(summary.full_coverage_at_10.total_cases, 16);
  }

  assert.deepEqual(result.public_examples.map((item) => item.role), ["success", "failure", "failure"]);
  assert.match(page, /import retrievalCheckup from "\.\.\/lib\/retrieval-checkup-v1\.json"/);
  assert.doesNotMatch(page, /14\s*\/\s*16|16\s*\/\s*16/);
});

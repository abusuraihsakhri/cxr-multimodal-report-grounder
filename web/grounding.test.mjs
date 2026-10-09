import test from "node:test";
import assert from "node:assert/strict";
import { analyzeFindings } from "./grounding.mjs";

test("maps right pleural effusion to the matching costophrenic template", () => {
  const result = analyzeFindings("CXR-01", "Right pleural effusion");
  assert.equal(result.totalMentions, 1);
  assert.equal(result.mappedMentions, 1);
  assert.equal(result.findings[0].anatomicalRegion, "right_costophrenic_angle");
  assert.equal(result.findings[0].boundingBox.x_min, 0.10);
});

test("cardiomegaly maps to cardiac silhouette", () => {
  const result = analyzeFindings("STUDY-1", "Cardiomegaly");
  assert.equal(result.findings[0].anatomicalRegion, "cardiac_silhouette");
  assert.equal(result.findings[0].category, "cardiac");
});

test("negated statements never receive positive anatomical annotations", () => {
  for (const text of ["No pneumothorax", "Without pleural effusion", "Negative for pneumonia"]) {
    const result = analyzeFindings("STUDY-1", text);
    assert.equal(result.mappedMentions, 0);
    assert.equal(result.findings[0].positiveFinding, false);
    assert.equal(result.findings[0].boundingBox, null);
  }
});

test("unrecognized terms are not invented or counted as localized", () => {
  const result = analyzeFindings("STUDY-1", "Normal chest\nUnrecognized finding");
  assert.equal(result.totalMentions, 2);
  assert.equal(result.mappedMentions, 0);
});

test("laterality selects the matching side or bilateral union", () => {
  assert.equal(analyzeFindings("ID1", "Left pleural effusion").findings[0].anatomicalRegion,
    "left_costophrenic_angle");
  const both = analyzeFindings("ID1", "Bilateral pleural effusion").findings[0];
  assert.equal(both.boundingBox.x_min, 0.10);
  assert.equal(both.boundingBox.x_max, 0.90);
});

test("input validation rejects malformed IDs, empty text, and excess lines", () => {
  assert.throws(() => analyzeFindings("../secret", "Cardiomegaly"));
  assert.throws(() => analyzeFindings("TEST", " \n "));
  assert.throws(() => analyzeFindings("TEST", "Cardiomegaly\n".repeat(101)));
  assert.throws(() => analyzeFindings("TEST", "x".repeat(401)));
});

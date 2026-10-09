// Deterministic report-term to anatomy templates; this does not inspect image pixels.
const REGIONS = Object.freeze({
  right_upper_lung: [0.10, 0.05, 0.45, 0.35],
  left_upper_lung: [0.55, 0.05, 0.90, 0.35],
  right_lower_lung: [0.10, 0.35, 0.45, 0.70],
  left_lower_lung: [0.55, 0.35, 0.90, 0.70],
  right_costophrenic_angle: [0.10, 0.65, 0.40, 0.85],
  left_costophrenic_angle: [0.60, 0.65, 0.90, 0.85],
  cardiac_silhouette: [0.30, 0.25, 0.70, 0.70],
  mediastinum: [0.35, 0.05, 0.65, 0.40],
  right_hilum: [0.25, 0.25, 0.45, 0.40],
  left_hilum: [0.55, 0.25, 0.75, 0.40],
  aortic_arch: [0.30, 0.15, 0.65, 0.30],
  trachea: [0.43, 0.02, 0.57, 0.25],
  spine: [0.45, 0.05, 0.55, 0.85],
});
const RULES = [
  ["pleural_effusion", ["right_costophrenic_angle", "left_costophrenic_angle"]],
  ["pneumothorax", ["right_upper_lung", "left_upper_lung"]],
  ["cardiomegaly", ["cardiac_silhouette"]],
  ["consolidation", ["right_lower_lung", "left_lower_lung"]],
  ["atelectasis", ["right_lower_lung", "left_lower_lung"]],
  ["opacity", ["right_upper_lung", "left_upper_lung"]],
  ["nodule", ["right_upper_lung", "left_upper_lung"]],
  ["mass", ["right_upper_lung", "left_upper_lung"]],
  ["pneumonia", ["right_lower_lung", "left_lower_lung"]],
  ["hilar_enlargement", ["right_hilum", "left_hilum"]],
  ["mediastinal_widening", ["mediastinum"]],
  ["aortic_enlargement", ["aortic_arch"]],
  ["tracheal_deviation", ["trachea"]],
  ["fracture", ["spine"]],
  ["edema", ["right_lower_lung", "left_lower_lung"]],
];
const NEGATED = /^(?:no\b|without\b|negative for\b|absence of\b)/i;
function lateralityOf(text) {
  if (/\b(bilateral|both)\b/i.test(text)) return "bilateral";
  if (/\bright\b/i.test(text)) return "right";
  if (/\bleft\b/i.test(text)) return "left";
  return null;
}
function categoryOf(text) {
  if (/\b(pleural|effusion|pneumothorax)\b/i.test(text)) return "pleural";
  if (/\b(heart|cardiac|cardiomegaly)\b/i.test(text)) return "cardiac";
  if (/\b(lung|pulmonary|pneumonia|nodule|mass|opacity|atelectasis|consolidation)\b/i.test(text)) return "pulmonary";
  if (/\b(mediastinal|hilar|aortic|trachea)\b/i.test(text)) return "mediastinal";
  if (/\b(fracture|rib|vertebral|spine)\b/i.test(text)) return "skeletal";
  if (/\b(device|catheter|pacemaker|line|tube)\b/i.test(text)) return "device";
  return "other";
}
export function analyzeFindings(studyId, rawText) {
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(studyId)) {
    throw new Error("Study ID must be 1–64 characters: letters, numbers, hyphens or underscores.");
  }
  if (typeof rawText !== "string" || rawText.length > 20000) {
    throw new Error("Finding text must be 20,000 characters or fewer.");
  }
  const lines = rawText.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  if (!lines.length) throw new Error("Enter at least one finding, one per line.");
  if (lines.length > 100 || lines.some(s => s.length > 400)) {
    throw new Error("Maximum 100 findings and 400 characters per finding.");
  }
  const findings = lines.map((text, index) => {
    const side = lateralityOf(text);
    const category = categoryOf(text);
    const positiveFinding = !NEGATED.test(text);
    const keyText = text.toLowerCase().replace(/[\s-]+/g, "_");
    let regionNames = null;
    if (positiveFinding) {
      for (const [term, names] of RULES) {
        if (keyText.includes(term)) { regionNames = names; break; }
      }
    }
    let anatomy = null;
    let box = null;
    if (regionNames) {
      const selected = side && side !== "bilateral"
        ? regionNames.filter(name => name.startsWith(side + "_"))
        : regionNames;
      const usable = selected.length ? selected : regionNames;
      const bounds = usable.map(name => REGIONS[name]).filter(Boolean);
      if (bounds.length) {
        anatomy = usable.join(" + ");
        box = {
          x_min: Math.min(...bounds.map(b => b[0])),
          y_min: Math.min(...bounds.map(b => b[1])),
          x_max: Math.max(...bounds.map(b => b[2])),
          y_max: Math.max(...bounds.map(b => b[3])),
        };
      }
    }
    return { index: index + 1, text, category, laterality: side,
      positiveFinding, templateMatched: Boolean(box), anatomicalRegion: anatomy, boundingBox: box };
  });
  return { studyId, method: "Rule-based anatomical templates; no pixels analyzed",
    coordinateSystem: "Normalized image extent, origin at top left, PA/AP orientation assumed",
    totalMentions: findings.length,
    mappedMentions: findings.filter(f => f.templateMatched).length, findings };
}

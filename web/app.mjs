import { analyzeFindings } from "./grounding.mjs";

const element = id => document.getElementById(id);
const form = element("ground-form");
const overlay = element("overlay");
const results = element("finding-list");
let current = null;

function setStatus(message, error = false) {
  element("status").textContent = message;
  element("status").classList.toggle("error", error);
}
function draw() {
  overlay.replaceChildren();
  if (!current) return;
  current.findings.filter(x => x.boundingBox).forEach(item => {
    const b = item.boundingBox;
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", 100 * b.x_min);
    rect.setAttribute("y", 100 * b.y_min);
    rect.setAttribute("width", 100 * (b.x_max - b.x_min));
    rect.setAttribute("height", 100 * (b.y_max - b.y_min));
    overlay.append(rect);
  });
}
form.addEventListener("submit", event => {
  event.preventDefault();
  try {
    current = analyzeFindings(element("study-id").value.trim(), element("findings").value);
    results.replaceChildren();
    current.findings.forEach(item => {
      const row = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = item.index + ". " + item.text;
      const detail = document.createElement("small");
      detail.textContent = item.templateMatched ? item.anatomicalRegion.replaceAll("_", " ")
        : item.positiveFinding ? "No anatomical template matched" : "Negated; not localized";
      row.append(title, detail);
      results.append(row);
    });
    element("list-placeholder").hidden = true;
    element("total").textContent = current.totalMentions;
    element("mapped").textContent = current.mappedMentions;
    element("export").disabled = false;
    draw();
    setStatus("Mapped " + current.mappedMentions + " of " + current.totalMentions + " mentions.");
  } catch (error) {
    current = null;
    element("export").disabled = true;
    overlay.replaceChildren();
    setStatus(error.message, true);
  }
});

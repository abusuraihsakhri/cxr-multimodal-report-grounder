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

let selectedImageURL = null;
const fileInput = element("image-file");
fileInput.addEventListener("change", () => {
  if (selectedImageURL) URL.revokeObjectURL(selectedImageURL);
  selectedImageURL = null;
  element("image-wrapper").hidden = true;
  element("image-placeholder").hidden = false;
  const file = fileInput.files?.[0];
  if (!file) return;
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 20 * 1024 * 1024) {
    fileInput.value = "";
    setStatus("Choose a PNG, JPEG or WebP image up to 20 MB.", true);
    return;
  }
  const preview = element("preview-img");
  selectedImageURL = URL.createObjectURL(file);
  preview.onload = () => {
    element("image-wrapper").hidden = false;
    element("image-placeholder").hidden = true;
    draw();
    setStatus("Local image loaded; no pixels have been analyzed.");
  };
  preview.onerror = () => setStatus("Unable to display this image.", true);
  preview.src = selectedImageURL;
});
for (const id of ["study-id", "findings"]) {
  element(id).addEventListener("input", () => {
    current = null;
    element("export").disabled = true;
    overlay.replaceChildren();
  });
}
window.addEventListener("pagehide", () => {
  if (selectedImageURL) URL.revokeObjectURL(selectedImageURL);
});

element("export").addEventListener("click", () => {
  if (!current) return;
  const data = JSON.stringify(current, null, 2);
  const url = URL.createObjectURL(new Blob([data], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = current.studyId + "-templates.json";
  link.click();
  URL.revokeObjectURL(url);
});

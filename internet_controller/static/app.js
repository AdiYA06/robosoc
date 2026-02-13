const state = { mode: "stop", vx: 0, vy: 0, turn: 0, speed: 0.4, height: 0 };
let session = "";
let ownerName = "operator";

const statusEl = document.getElementById("status");
const ownerEl = document.getElementById("owner");
const tokenEl = document.getElementById("token");
const connectBtn = document.getElementById("connect");
const speedEl = document.getElementById("speed");
const heightEl = document.getElementById("height");
const moveReadout = document.getElementById("move-readout");
const turnReadout = document.getElementById("turn-readout");
const moveKnob = document.getElementById("move-knob");
const turnKnob = document.getElementById("turn-knob");

speedEl.addEventListener("input", () => state.speed = Number(speedEl.value));
heightEl.addEventListener("input", () => state.height = Number(heightEl.value));

function resolveMode() {
  if (Math.abs(state.turn) > 0.001) return "turn";
  if (Math.abs(state.vx) > 0.001 || Math.abs(state.vy) > 0.001) return "walk";
  return "stop";
}

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return res.json();
}

connectBtn.addEventListener("click", async () => {
  ownerName = ownerEl.value || "operator";
  const login = await post("/api/login", { token: tokenEl.value, owner: ownerName });
  if (!login.ok) { statusEl.textContent = "Login failed"; return; }
  session = login.session;
  const claim = await post("/api/claim", { session, owner: ownerName });
  statusEl.textContent = claim.ok ? `Control locked by ${ownerName}` : `Busy: ${claim.owner || "unknown"}`;
});

function makePad(padId, knobId, onChange, horizontalOnly = false) {
  const pad = document.getElementById(padId);
  const knob = document.getElementById(knobId);
  function update(clientX, clientY) {
    const rect = pad.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const r = rect.width / 2;
    let dx = (clientX - cx) / r;
    let dy = (clientY - cy) / r;
    const mag = Math.hypot(dx, dy);
    if (mag > 1) { dx /= mag; dy /= mag; }
    if (horizontalOnly) dy = 0;
    knob.style.left = `${50 + dx * 35}%`;
    knob.style.top = `${50 + dy * 35}%`;
    onChange(dx, -dy);
  }
  function reset() {
    knob.style.left = "50%";
    knob.style.top = "50%";
    onChange(0, 0);
  }
  pad.addEventListener("pointerdown", e => { pad.setPointerCapture(e.pointerId); update(e.clientX, e.clientY); });
  pad.addEventListener("pointermove", e => { if (pad.hasPointerCapture(e.pointerId)) update(e.clientX, e.clientY); });
  pad.addEventListener("pointerup", reset);
  pad.addEventListener("pointercancel", reset);
}

makePad("move-pad", "move-knob", (x, y) => {
  state.vx = Number(y.toFixed(3));
  state.vy = Number(x.toFixed(3));
  moveReadout.textContent = `vx ${state.vx.toFixed(2)} | vy ${state.vy.toFixed(2)}`;
});
makePad("turn-pad", "turn-knob", x => {
  state.turn = Number(x.toFixed(3));
  turnReadout.textContent = `turn ${state.turn.toFixed(2)}`;
}, true);

const pressed = new Set();
const keys = new Set(["w","a","s","d","j","k"]);
function drawKeyboard() {
  moveKnob.style.left = `${50 + state.vy * 35}%`;
  moveKnob.style.top = `${50 - state.vx * 35}%`;
  turnKnob.style.left = `${50 + state.turn * 35}%`;
  turnKnob.style.top = "50%";
}
function applyKeys() {
  state.vx = (pressed.has("w") ? 1 : 0) + (pressed.has("s") ? -1 : 0);
  state.vy = (pressed.has("d") ? 1 : 0) + (pressed.has("a") ? -1 : 0);
  state.turn = (pressed.has("k") ? 1 : 0) + (pressed.has("j") ? -1 : 0);
  moveReadout.textContent = `vx ${state.vx.toFixed(2)} | vy ${state.vy.toFixed(2)}`;
  turnReadout.textContent = `turn ${state.turn.toFixed(2)}`;
  drawKeyboard();
}
window.addEventListener("keydown", e => {
  const k = e.key.toLowerCase();
  if (!keys.has(k)) return;
  e.preventDefault();
  pressed.add(k); applyKeys();
});
window.addEventListener("keyup", e => {
  const k = e.key.toLowerCase();
  if (!keys.has(k)) return;
  e.preventDefault();
  pressed.delete(k); applyKeys();
});

async function tick() {
  if (!session) return;
  state.mode = resolveMode();
  const cmd = await post("/api/command", { ...state, session });
  if (!cmd.ok) {
    statusEl.textContent = `Lost control: ${cmd.error}`;
    session = "";
    return;
  }
  await post("/api/renew", { session });
  statusEl.textContent = `Controlling (${ownerName})`;
}
setInterval(tick, 40);

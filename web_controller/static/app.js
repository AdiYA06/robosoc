const state = {
  mode: "stop",
  vx: 0,
  vy: 0,
  turn: 0,
  speed: 0.4,
  height: 0,
};

const connectionEl = document.getElementById("connection");
const speedEl = document.getElementById("speed");
const heightEl = document.getElementById("height");
const moveReadout = document.getElementById("move-readout");
const turnReadout = document.getElementById("turn-readout");
const moveKnob = document.getElementById("move-knob");
const turnKnob = document.getElementById("turn-knob");

speedEl.addEventListener("input", () => {
  state.speed = Number(speedEl.value);
});
heightEl.addEventListener("input", () => {
  state.height = Number(heightEl.value);
});

function makePad(padId, knobId, onChange, options = {}) {
  const pad = document.getElementById(padId);
  const knob = document.getElementById(knobId);
  const horizontalOnly = Boolean(options.horizontalOnly);

  function update(clientX, clientY) {
    const rect = pad.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const r = rect.width / 2;

    let dx = (clientX - cx) / r;
    let dy = (clientY - cy) / r;
    const mag = Math.hypot(dx, dy);
    if (mag > 1) {
      dx /= mag;
      dy /= mag;
    }
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

  pad.addEventListener("pointerdown", (e) => {
    pad.setPointerCapture(e.pointerId);
    update(e.clientX, e.clientY);
  });
  pad.addEventListener("pointermove", (e) => {
    if (pad.hasPointerCapture(e.pointerId)) update(e.clientX, e.clientY);
  });
  pad.addEventListener("pointerup", reset);
  pad.addEventListener("pointercancel", reset);
}

makePad("move-pad", "move-knob", (x, y) => {
  state.vx = Number(y.toFixed(3));
  state.vy = Number(x.toFixed(3));
  moveReadout.textContent = `vx ${state.vx.toFixed(2)} | vy ${state.vy.toFixed(2)}`;
});

makePad("turn-pad", "turn-knob", (x) => {
  state.turn = Number(x.toFixed(3));
  turnReadout.textContent = `turn ${state.turn.toFixed(2)}`;
}, { horizontalOnly: true });

function renderKeyboardOverlay() {
  moveKnob.style.left = `${50 + state.vy * 35}%`;
  moveKnob.style.top = `${50 - state.vx * 35}%`;
  turnKnob.style.left = `${50 + state.turn * 35}%`;
  turnKnob.style.top = "50%";
  moveReadout.textContent = `vx ${state.vx.toFixed(2)} | vy ${state.vy.toFixed(2)}`;
  turnReadout.textContent = `turn ${state.turn.toFixed(2)}`;
}

function resolveMode() {
  const turning = Math.abs(state.turn) > 0.001;
  const walking = Math.abs(state.vx) > 0.001 || Math.abs(state.vy) > 0.001;
  if (turning) return "turn";
  if (walking) return "walk";
  return "stop";
}

const pressed = new Set();
const keyMap = new Set(["w", "a", "s", "d", "j", "k"]);

function applyKeyboardState() {
  const vx = (pressed.has("w") ? 1 : 0) + (pressed.has("s") ? -1 : 0);
  const vy = (pressed.has("d") ? 1 : 0) + (pressed.has("a") ? -1 : 0);
  const turn = (pressed.has("k") ? 1 : 0) + (pressed.has("j") ? -1 : 0);
  state.vx = vx;
  state.vy = vy;
  state.turn = turn;
  renderKeyboardOverlay();
}

window.addEventListener("keydown", (e) => {
  const key = e.key.toLowerCase();
  if (!keyMap.has(key)) return;
  if (e.target instanceof HTMLElement && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) {
    return;
  }
  e.preventDefault();
  pressed.add(key);
  applyKeyboardState();
});

window.addEventListener("keyup", (e) => {
  const key = e.key.toLowerCase();
  if (!keyMap.has(key)) return;
  e.preventDefault();
  pressed.delete(key);
  applyKeyboardState();
});

async function sendState() {
  state.mode = resolveMode();
  try {
    const res = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    connectionEl.textContent = `Connected - mode: ${state.mode}`;
  } catch {
    connectionEl.textContent = "Disconnected - retrying...";
  }
}

setInterval(sendState, 100);
window.addEventListener("beforeunload", () => {
  navigator.sendBeacon(
    "/api/control",
    JSON.stringify({ mode: "stop", vx: 0, vy: 0, turn: 0, speed: state.speed, height: state.height })
  );
});

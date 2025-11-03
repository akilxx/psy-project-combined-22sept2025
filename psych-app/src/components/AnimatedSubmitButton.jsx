// psych-app/src/components/AnimatedSubmitButton.jsx
import React, { useState } from "react";

export default function AnimatedSubmitButton({
  onClick,
  loading = false,
  duration = 1500,
  labels = ["Submit", "Submitting"],
  className = "",
  submittedBg = "#338764",      // 🔵 color to use AFTER it slides to "Submitting"
  submittedDelay = 250,         // ms delay so color change happens after the text slide
}) {
  const [state, setState] = useState("idle"); // 'idle' | 'downloading'

  const handleClick = (e) => {
    e.preventDefault();
    if (state === "downloading") return;
    setState("downloading");
    onClick?.();
  };

  return (
    <>
      <style>{css}</style>

      <a
        href="#"
        onClick={handleClick}
        className={`button ${loading ? "loading" : ""} ${className}`}
        data-state={state}
        style={{
          ["--duration"]: String(duration),
          ["--submitted-bg"]: submittedBg,
          ["--submitted-delay"]: `${submittedDelay}ms`,
        }}
      >
        <ul>
          <li>{labels[0]}</li>
          <li>{labels[1]}</li>
        </ul>
        <div aria-hidden="true" />
      </a>
    </>
  );
}

const css = `
.button {
  --background: #4BC793;
  --success: #338764; 
  --text: #fff;
  --arrow: #fff;
  --checkmark: #fff;
  --shadow: rgba(10, 22, 50, .24);
  

  display: inline-flex;
  align-items: stretch;
  overflow: hidden;
  text-decoration: none;
  -webkit-mask-image: -webkit-radial-gradient(white, black);
  background: var(--background);
  border-radius: 8px;
  transition: transform .2s ease, box-shadow .2s ease, background-color .2s ease;
  box-shadow: 0 6px 16px var(--shadow);
  user-select: none;
  
}
.button:active { transform: scale(.95); }

/* After it has slid to “Submitting”: switch background to submitted blue, after a slight delay */
.button[data-state="downloading"] {
  --background: var(--submitted-bg, #338764);
  transition-delay: var(--submitted-delay, 250ms);
}

/* 🔵 Hover turns blue only while "active" (not yet downloading) */
.button:not([data-state="downloading"]):hover {
  --background: #338764; /* blue on hover */
}

/* text stack */
.button ul {
  margin: 0;
  padding: 10px 24px;
  list-style: none;
  text-align: center;
  position: relative;
  backface-visibility: hidden;
  font-size: 14px;
  font-weight: 600;
  line-height: 22px;
  color: var(--text);
}
.button ul li:not(:first-child) {
  top: 10px; left: 0; right: 0; position: absolute;
}
.button ul li:nth-child(2) { top: 52px; }


/* Slide to “Submitting” */
.button[data-state="downloading"] ul {
  transition: transform 250ms ease;
  transform: translateY(-100%);
}

/* Optional loading animations */
.button.loading ul {
  animation: text calc(var(--duration) * 1ms) linear forwards calc(var(--duration) * .065ms);
}
.button.loading > div:before {
  animation: line calc(var(--duration) * 1ms) linear forwards calc(var(--duration) * .065ms);
}
.button.loading > div:after {
  animation: background calc(var(--duration) * 1ms) linear forwards calc(var(--duration) * .065ms);
}

/* keyframes */
@keyframes text {
  10%, 85%  { transform: translateY(-100%); }
  95%, 100% { transform: translateY(-200%); }
}
@keyframes line {
  5%, 10%   { transform: translateY(-30px); }
  40%       { transform: translateY(-20px); }
  65%       { transform: translateY(0); }
  75%, 100% { transform: translateY(30px); }
}
@keyframes background {
  10%   { transform: scaleY(0); }
  40%   { transform: scaleY(.15); }
  65%   { transform: scaleY(.5); border-radius: 0 0 50% 50%; }
  75%   { border-radius: 0 0 50% 50%; }
  90%,100% { border-radius: 0; }
  75%,100% { transform: scaleY(1); }
}
`;

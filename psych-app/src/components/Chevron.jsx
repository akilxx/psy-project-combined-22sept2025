// psych-app/src/components/Chevron.jsx

import React from "react";
import "./chevron.css";

/**
 * Chevron
 * Props:
 *  - size        (px)      : outer box size (default 60)
 *  - thickness   (px)      : border thickness of the chevron (default 6)
 *  - color                 : arrow color (default "black")
 *  - hoverColor            : arrow color on hover (default "blue")
 *  - scale                 : initial scale (default 0.6)
 *  - hoverScale            : hover scale (default 0.8)
 *  - direction             : "right" | "left" | "up" | "down" (default "right")
 *  - className             : extra class names for the wrapper
 */
export default function Chevron({
  size = 60,
  thickness = 6,
  color = "black",
  hoverColor = "blue",
  scale = 0.6,
  hoverScale = 0.8,
  direction = "right",
  className = "",
  ...rest
}) {
  // base rotation for a right-facing chevron is -45deg
  const baseRotations = {
    right: -45,
    left: 135,
    up: -135,
    down: 45,
  };
  const rotation = baseRotations[direction] ?? baseRotations.right;

  const vars = {
    "--chev-size": `${size}px`,
    "--chev-thickness": `${thickness}px`,
    "--chev-color": color,
    "--chev-hover-color": hoverColor,
    "--chev-scale": scale,
    "--chev-hover-scale": hoverScale,
    "--chev-rotate": `${rotation}deg`,
  };

  return (
    <div
      className={`arrow-chevron ${className}`}
      style={vars}
      aria-hidden="true"
      {...rest}
    >
      <span className="arrow" />
    </div>
  );
}

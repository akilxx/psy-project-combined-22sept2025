// psych-app/src/components/RippleButton.jsx

import React, { useState, useRef } from "react";

export default  function RippleButton({
  children,
  className = "",
  onClick,
  onPressStart,
  pressDelay = 400,
  ...rest
}) {
  const btnRef = useRef(null);
  const [ripple, setRipple] = useState(null); // {x, y, size, key}

  function handleClick(e) {
    const rect = btnRef.current.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;

    if (onPressStart) onPressStart(e);

    // Changing the key forces remount so the animation restarts
    setRipple({ x, y, size, key: Date.now() });

    // Pass click upstream after the configured delay
    if (onClick) setTimeout(() => onClick(e), pressDelay);
  }

  const base =
    "rounded px-5 py-3 min-w-max overflow-hidden shadow relative " +
    " focus:outline-none";

  return (
    <button
      type="button"
      ref={btnRef}
      onClick={handleClick}
      className={`${base} ${className}`}
      {...rest}
    >
      {children}
      {ripple && (
        <span
          key={ripple.key}
          className="ripple pointer-events-none"
          style={{
            left: ripple.x,
            top: ripple.y,
            width: ripple.size,
            height: ripple.size,
          }}
          onAnimationEnd={() => setRipple(null)} // tidy DOM after animation
        />
      )}
    </button>
  );
}

// psych-app/src/components/RippleButton.jsx
import React from "react";
import "./ripple-exact.css"; // include the ripple CSS below

export default function RippleButton({
  children,
  className = "",
  onClick,
  disabled,
  ...rest
}) {
  const [pressed, setPressed] = React.useState(false);
  const btnRef = React.useRef(null);
  const rippleRef = React.useRef(null);
  const circleRef = React.useRef(null);

  const base =
    "relative rounded px-5 py-3 min-w-max overflow-hidden shadow " +
    "focus:outline-none transition-transform duration-200 ease-out select-none";

  // This replicates your jQuery click handler logic exactly (but in React):
  const triggerExactRipple = (nativeEvt) => {
    if (!btnRef.current || !rippleRef.current || !circleRef.current) return;

    const rect = btnRef.current.getBoundingClientRect();
    // Original used pageX/pageY minus .parent().offset(); clientX/clientY vs rect is equivalent
    const clientX =
      nativeEvt.clientX ?? nativeEvt.touches?.[0]?.clientX ?? 0;
    const clientY =
      nativeEvt.clientY ?? nativeEvt.touches?.[0]?.clientY ?? 0;

    const x = clientX - rect.left;
    const y = clientY - rect.top;

    // Set top/left on the circle like `$circle.css({ top, left })`
    circleRef.current.style.top = `${y}px`;
    circleRef.current.style.left = `${x}px`;

    // Add 'is-active' to the .js-ripple container (same as $this.addClass('is-active'))
    rippleRef.current.classList.add("is-active");
  };

  const onPointerDown = (e) => {
    setPressed(true);
    triggerExactRipple(e.nativeEvent); // fire ripple on press (more reliable on mobile)
  };

  const onAnimEnd = () => {
    // Same as: $ripple.on('animationend ...', () => $(this).removeClass('is-active'));
    rippleRef.current?.classList.remove("is-active");
  };

  return (
    <button
      ref={btnRef}
      type="button"
      disabled={disabled}
      onPointerDown={onPointerDown}
      onPointerUp={() => setPressed(false)}
      onPointerCancel={() => setPressed(false)}
      onPointerLeave={() => setPressed(false)}
      onClick={onClick}
      className={`${base} ${pressed ? "scale-95" : "scale-100"} ${className}`}
      style={{ touchAction: "manipulation", WebkitTapHighlightColor: "transparent" }}
      {...rest}
    >
      {/* EXACT structure from your HTML */}
      <div
        className="c-ripple js-ripple"
        ref={rippleRef}
        onAnimationEnd={onAnimEnd}
      >
        <span className="c-ripple__circle" ref={circleRef}></span>
      </div>

      {/* Content above ripple */}
      <span className="relative z-10">{children}</span>
    </button>
  );
}

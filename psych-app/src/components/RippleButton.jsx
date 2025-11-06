// psych-app/src/components/RippleButton.jsx
import React from "react";
import "./ripple-exact.css"; // your existing ripple CSS

export default function RippleButton({
  children,
  className = "",
  onClick,          // ← will run only after ripple completes
  disabled,
  ...rest
}) {
  const [pressed, setPressed] = React.useState(false);
  const [busy, setBusy]       = React.useState(false); // block double taps
  const btnRef     = React.useRef(null);
  const rippleRef  = React.useRef(null);
  const circleRef  = React.useRef(null);
  const timeoutRef = React.useRef(null);               // safety fallback

  const base =
    "relative rounded px-5 py-3 min-w-max overflow-hidden " +
    "transition-transform duration-200 ease-out select-none";

  // Clean up any pending fallback if unmounted
  React.useEffect(() => () => clearTimeout(timeoutRef.current), []);

  const runAfterRipple = (cb) => {
    // Listen exactly once for the animation end
    const el = rippleRef.current;
    if (!el) return cb?.();

    const finish = () => {
      el.classList.remove("is-active");
      el.removeEventListener("animationend", finish);
      clearTimeout(timeoutRef.current);
      setBusy(false);
      cb?.();
    };

    el.addEventListener("animationend", finish, { once: true });

    // Safety fallback: if for any reason animationend doesn’t fire,
    // run the callback slightly after the CSS duration (400ms).
    timeoutRef.current = setTimeout(finish, 420);
  };

  const triggerExactRipple = (nativeEvt) => {
    if (!btnRef.current || !rippleRef.current || !circleRef.current) return;

    const rect = btnRef.current.getBoundingClientRect();
    const clientX = nativeEvt.clientX ?? nativeEvt.touches?.[0]?.clientX ?? rect.left + rect.width / 2;
    const clientY = nativeEvt.clientY ?? nativeEvt.touches?.[0]?.clientY ?? rect.top + rect.height / 2;
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    circleRef.current.style.top = `${y}px`;
    circleRef.current.style.left = `${x}px`;
    rippleRef.current.classList.add("is-active");
  };

  const onPointerDown = (e) => {
    if (disabled || busy) return;
    setPressed(true);
    setBusy(true);                     // block immediate actions
    triggerExactRipple(e.nativeEvent); // start ripple now

    // IMPORTANT: don’t let the native click fire upstream yet.
    // We’ll call the user’s onClick in runAfterRipple().
    e.preventDefault();
  };

  const onPointerUp = () => setPressed(false);

  const onKeyDown = (e) => {
    // keyboard accessibility: Enter/Space should also ripple + gate
    if (disabled || busy) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setPressed(true);
      setBusy(true);
      triggerExactRipple(e.nativeEvent ?? e);
    }
  };
  const onKeyUp = () => setPressed(false);

  // Once the ripple ends, run the actual onClick (if provided)
  React.useEffect(() => {
    if (!busy) return;
    runAfterRipple(() => onClick?.());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busy]); // runs whenever we set busy=true (i.e., a new ripple starts)

  return (
    <button
      ref={btnRef}
      type="button"
      disabled={disabled || busy}
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onPointerLeave={onPointerUp}
      onKeyDown={onKeyDown}
      onKeyUp={onKeyUp}
      // We intentionally DO NOT forward onClick to the native button.
      // It will run after ripple via runAfterRipple().
      className={`${base} ${pressed ? "scale-95" : "scale-100"} ${className}`}
      style={{ touchAction: "manipulation", WebkitTapHighlightColor: "transparent" }}
      {...rest}
    >
      {/* ripple layer */}
      <div className="c-ripple js-ripple" ref={rippleRef}>
        <span className="c-ripple__circle" ref={circleRef} />
      </div>

      {/* content */}
      <span className="relative z-10">{children}</span>
    </button>
  );
}

// psych-app/src/components/ModifiedCard.jsx
import clsx from "clsx";

/**
 * A fluid, midnight-blue card that grows with the viewport.
 * – Plain JavaScript, works in .jsx projects without TypeScript
 * – Props:
 *     • children   – card contents
 *     • className  – extra/override Tailwind classes
 *     • …rest      – any other native <div> props (id, role, onClick, etc.)
 */
const ModifiedCard = ({ children, className, ...rest }) => (
  <div
    {...rest}
    className={clsx(
      /* base look & feel */
      "rounded-[40px] cursor-pointer relative text-white mx-auto",

      /* fluid sizing */
      "w-full max-w-[90vw] h-auto max-h-[95vh]",

      /* gradient background + fancy shadow */
      // "bg-gradient-to-tr from-[#354AF5] to-[#182FCA]",
      // "shadow-[0_10px_30px_5px_rgba(0,0,0,0.2),_0_0_6px_rgba(51,76,221,0.8),_0_0_12px_rgba(51,76,221,0.6),_inset_0_3px_8px_rgba(0,0,0,0.14),_0_0_0_1px_#172691]",

      /* caller-supplied overrides */
      className
    )}
  >
    {children}
  </div>
);

export default ModifiedCard;

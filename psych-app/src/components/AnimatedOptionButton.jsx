// psych-app/src/components/AnimatedOptionButton.jsx
import styles from './AnimatedOptionButton.module.scss';

function AnimatedOptionButton({
  label,
  selected = false,
  loading = false,
  disabled = false,
  onClick,
  ...rest
}) {
  const handleClick = event => {
    if (disabled || loading) {
      event.preventDefault();
      return;
    }

    if (onClick) onClick(event);
  };

  const className = [
    styles.optionButton,
    selected ? styles.selected : '',
    loading ? styles.loading : '',
    disabled ? styles.disabled : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type="button"
      {...rest}
      onClick={handleClick}
      className={className}
      disabled={disabled || loading}
      aria-pressed={selected}
      aria-busy={loading}
    >
      <span className={styles.content}>
        <span className={styles.label}>{label}</span>
        <span className={styles.glow} aria-hidden="true" />
        <span className={styles.pulseRing} aria-hidden="true" />
        {loading && (
          <span className={styles.loader} role="status" aria-live="polite">
            <span className={styles.visuallyHidden}>Saving…</span>
          </span>
        )}
      </span>
    </button>
  );
}

export default AnimatedOptionButton;

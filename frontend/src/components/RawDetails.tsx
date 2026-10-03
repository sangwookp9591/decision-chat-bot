/** Original internal codes / JSON, folded away from the regular view. */
export function RawDetails({ children, label = '자세히' }: { children: unknown; label?: string }) {
  const text = typeof children === 'string' ? children : JSON.stringify(children, null, 2);
  return <details className="raw-details"><summary>{label}</summary><pre>{text}</pre></details>;
}

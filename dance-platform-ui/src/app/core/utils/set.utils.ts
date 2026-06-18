export function toggleSet<T>(s: Set<T>, item: T): Set<T> {
  const next = new Set(s);
  next.has(item) ? next.delete(item) : next.add(item);
  return next;
}

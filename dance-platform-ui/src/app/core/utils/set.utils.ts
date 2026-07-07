export function toggleSet<T>(s: Set<T>, item: T): Set<T> {
  const next = new Set(s);
  next.has(item) ? next.delete(item) : next.add(item);
  return next;
}

/**
 * Array counterpart of {@link toggleSet}: returns a new array with `item` removed if it
 * was present, or appended if it wasn't. Used where the caller keeps a plain `number[]`
 * of selected ids (e.g. the edit-dance multi-selects) rather than a `Set`.
 */
export function toggleInArray<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item];
}

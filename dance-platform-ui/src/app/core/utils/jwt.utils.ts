/** Reads the signed `isAdmin` claim from a JWT without verifying the signature
 *  (the server enforces that on every request). Returns true/false when the claim is
 *  present, or null for a missing claim / malformed token — callers treat null as
 *  non-admin (e.g. legacy tokens issued before the claim existed). */
export function jwtIsAdmin(token: string | null): boolean | null {
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    const json = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(json) as { isAdmin?: unknown };
    if (payload.isAdmin === undefined) return null;
    return payload.isAdmin === true || payload.isAdmin === 'true';
  } catch {
    return null;
  }
}

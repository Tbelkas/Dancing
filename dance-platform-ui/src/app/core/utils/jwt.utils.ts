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

/** True when the token's `exp` claim is in the past, so the client can avoid showing a flash of
 *  authed UI for a session the server will reject. A missing/malformed exp is treated as NOT expired
 *  (let the server stay the authority) rather than locking the user out on a parse quirk. */
export function isTokenExpired(token: string | null): boolean {
  if (!token) return true;
  const parts = token.split('.');
  if (parts.length !== 3) return false;
  try {
    const json = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(json) as { exp?: unknown };
    if (typeof payload.exp !== 'number') return false;
    return payload.exp * 1000 <= Date.now();
  } catch {
    return false;
  }
}

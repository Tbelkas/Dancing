import { describe, it, expect } from 'vitest';
import { jwtIsAdmin } from './jwt.utils';

/** Builds a JWT-shaped string (header.payload.signature) carrying the given claims. */
function tokenWith(claims: Record<string, unknown>): string {
  const b64 = (o: object) => Buffer.from(JSON.stringify(o)).toString('base64url');
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(claims)}.signature`;
}

describe('jwtIsAdmin', () => {
  it('reads the string claim "true"', () => {
    expect(jwtIsAdmin(tokenWith({ isAdmin: 'true' }))).toBe(true);
  });

  it('reads the string claim "false"', () => {
    expect(jwtIsAdmin(tokenWith({ isAdmin: 'false' }))).toBe(false);
  });

  it('also accepts a boolean true', () => {
    expect(jwtIsAdmin(tokenWith({ isAdmin: true }))).toBe(true);
  });

  it('returns null when the claim is absent (legacy token)', () => {
    expect(jwtIsAdmin(tokenWith({ sub: '6', name: 'tbelkas' }))).toBeNull();
  });

  it('returns null for null, empty, or malformed tokens', () => {
    expect(jwtIsAdmin(null)).toBeNull();
    expect(jwtIsAdmin('')).toBeNull();
    expect(jwtIsAdmin('only.two')).toBeNull();
    expect(jwtIsAdmin('a.!!!.c')).toBeNull();
  });
});

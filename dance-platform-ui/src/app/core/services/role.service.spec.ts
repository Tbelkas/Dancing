import { describe, it, expect, beforeEach } from 'vitest';
import { RoleService } from './role.service';

// These specs run in vitest's node environment, which has no DOM. RoleService reads and
// writes localStorage on construction, so stand up just enough of it to be real.
const store = new Map<string, string>();
globalThis.localStorage = {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, String(v)),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
  key: (i: number) => [...store.keys()][i] ?? null,
  get length() { return store.size; }
} as Storage;

/** Builds a JWT-shaped string (header.payload.signature) carrying the given claims. */
function tokenWith(claims: Record<string, unknown>): string {
  const b64 = (o: object) => Buffer.from(JSON.stringify(o)).toString('base64url');
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(claims)}.signature`;
}

const adminToken = tokenWith({ isAdmin: true });

/** A new instance re-reads localStorage, which is what a page reload does. */
function freshService(): RoleService {
  return new RoleService();
}

describe('RoleService', () => {
  beforeEach(() => localStorage.clear());

  it('grants admin UI to an admin token by default', () => {
    const role = freshService();
    role.loadFromToken(adminToken);
    expect(role.isSuperAdmin()).toBe(true);
    expect(role.isAdmin()).toBe(true);
  });

  it('withholds admin UI once the mode is switched off, without dropping the capability', () => {
    const role = freshService();
    role.loadFromToken(adminToken);
    role.setAdminMode(false);
    // The distinction the whole feature rests on: still an admin, just not looking like one.
    expect(role.isSuperAdmin()).toBe(true);
    expect(role.isAdmin()).toBe(false);
  });

  it('never grants admin UI to a non-admin, whatever the mode says', () => {
    const role = freshService();
    role.setAdminMode(true);
    role.loadFromToken(tokenWith({ isAdmin: false }));
    expect(role.isAdmin()).toBe(false);
    role.loadFromToken(null);
    expect(role.isAdmin()).toBe(false);
  });

  it('remembers the mode across a reload', () => {
    freshService().setAdminMode(false);
    const reloaded = freshService();
    expect(reloaded.adminMode()).toBe(false);
  });

  it('defaults to on for an account that never touched the toggle', () => {
    expect(freshService().adminMode()).toBe(true);
  });

  it('signing out clears the claim but leaves the chosen view alone', () => {
    const role = freshService();
    role.loadFromToken(adminToken);
    role.setAdminMode(false);
    role.clearRole();
    expect(role.isSuperAdmin()).toBe(false);
    expect(role.adminMode()).toBe(false);
  });
});

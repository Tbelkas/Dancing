/** A provider the server has credentials for. The login page renders one button per entry, so an
 *  unconfigured provider simply never appears rather than offering a dead button. */
export interface ExternalProvider {
  name: string;
  displayName: string;
}

/** What the server can tell us about a half-finished social sign-up, before the account exists. */
export interface SignupTicket {
  provider: string;
  email: string | null;
  name: string | null;
  suggestedUsername: string;
}

export interface LinkedAccount {
  provider: string;
  displayName: string;
  email: string | null;
  linkedAt: string;
}

export interface LinkedAccounts {
  accounts: LinkedAccount[];
  /** False when a social login is the account's only way in — the UI hides the last Unlink
   *  button instead of letting the user lock themselves out. */
  hasPassword: boolean;
}

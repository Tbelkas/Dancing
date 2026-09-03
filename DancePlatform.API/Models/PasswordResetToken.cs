namespace DancePlatform.API.Models;

/// <summary>
/// A single-use, short-lived permission to set a new password without knowing the old one.
///
/// Only the SHA-256 of the token is stored: the plaintext exists in the user's mailbox and
/// nowhere else, so a database dump (or a backup pulled to a laptop) doesn't hand anyone a
/// working key to every account that has recently asked for a reset.
/// </summary>
public class PasswordResetToken
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public User User { get; set; } = null!;

    /// Base64 SHA-256 of the token that was mailed out. Never the token itself.
    public string TokenHash { get; set; } = string.Empty;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime ExpiresAt { get; set; }

    /// Set the moment the token is spent, so a link forwarded, cached or logged somewhere
    /// can't be replayed. A non-null value here is as good as expired.
    public DateTime? UsedAt { get; set; }
}

namespace DancePlatform.API.Models;

/// A sign-in method owned by an external identity provider (Google, Facebook).
/// A user may hold several — one per provider — alongside or instead of a password.
public class UserLogin
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public User User { get; set; } = null!;

    /// Lower-case provider key ("google", "facebook"), matching IExternalAuthProvider.Name.
    public string Provider { get; set; } = string.Empty;

    /// The provider's own immutable subject id. This — never the email — is what identifies
    /// the account: emails get reassigned, and providers differ on whether they verify them.
    public string ProviderUserId { get; set; } = string.Empty;

    /// The address the provider reported at link time, kept for display only.
    public string? Email { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

namespace DancePlatform.API.Services.ExternalAuth;

/// What a provider tells us about the person who just signed in.
/// <param name="Subject">The provider's immutable id for this user — the identity we key on.</param>
public record ExternalIdentity(string Subject, string? Email, string? Name, string? AvatarUrl);

/// One external identity provider (Google, Facebook). Implementations own the provider-specific
/// half of the OAuth authorization-code flow; the controller owns the half that is the same for
/// everyone (state, PKCE, account lookup, token issuance).
public interface IExternalAuthProvider
{
    /// Lower-case key used in URLs and stored in UserLogin.Provider.
    string Name { get; }

    /// Label for the sign-in button.
    string DisplayName { get; }

    /// False when credentials are absent — a dev box with no secrets simply offers no button
    /// rather than sending people to a broken consent screen.
    bool IsConfigured { get; }

    string BuildAuthorizeUrl(string redirectUri, string state, string codeChallenge);

    /// Redeems the authorization code. Returns null if the provider rejects it or the response
    /// fails validation. Implementations must verify that the token they receive was issued for
    /// *this* app before trusting any profile data in it.
    Task<ExternalIdentity?> ExchangeCodeAsync(
        string code, string redirectUri, string codeVerifier, CancellationToken ct);
}

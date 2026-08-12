using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Caching.Memory;

namespace DancePlatform.API.Services.ExternalAuth;

/// <param name="LinkUserId">
/// Set when the flow was started from the profile page to attach a provider to an account that
/// already exists; null for a plain sign-in. Carried inside the signed blob because the callback
/// is a top-level browser navigation with no Authorization header to read.
/// </param>
public record OAuthState(
    string Provider, string CodeVerifier, string Nonce, long ExpiresAtUnix, int? LinkUserId);

/// Signs the `state` parameter that rides along through the provider's consent screen and comes
/// back on the callback.
///
/// Two things depend on this being right. The signature is what makes the callback safe: without
/// it anyone could invoke our callback URL with a code of their choosing (CSRF login). And the
/// PKCE verifier has to survive the round-trip *without* being readable by the browser, which is
/// why it travels inside the signed blob rather than in a cookie or in localStorage.
///
/// HMAC over the JWT signing key rather than IDataProtection: the Pi runs the API as a service
/// whose data-protection key ring isn't reliably persisted, and a key regenerated on restart
/// would silently break every in-flight sign-in. The JWT key is already required to be strong
/// and stable (see the boot guard in Program.cs).
public class OAuthStateProtector
{
    private readonly byte[] _key;
    private readonly IMemoryCache _cache;

    public static readonly TimeSpan Lifetime = TimeSpan.FromMinutes(15);

    public OAuthStateProtector(IConfiguration config, IMemoryCache cache)
    {
        _key = Encoding.UTF8.GetBytes(config["Jwt:Key"]!);
        _cache = cache;
    }

    public string Protect(OAuthState state)
    {
        var payload = Base64Url(JsonSerializer.SerializeToUtf8Bytes(state));
        return $"{payload}.{Sign(payload)}";
    }

    /// Returns null if the state is malformed, forged, expired, or already used.
    public OAuthState? Unprotect(string? value)
    {
        if (string.IsNullOrEmpty(value)) return null;

        var dot = value.IndexOf('.', StringComparison.Ordinal);
        if (dot <= 0 || dot == value.Length - 1) return null;

        var payload = value[..dot];
        var signature = value[(dot + 1)..];

        // Fixed-time comparison — a byte-at-a-time equality check here leaks the expected
        // signature to anyone willing to time enough callbacks.
        if (!CryptographicOperations.FixedTimeEquals(
                Encoding.UTF8.GetBytes(signature), Encoding.UTF8.GetBytes(Sign(payload))))
            return null;

        OAuthState? state;
        try
        {
            state = JsonSerializer.Deserialize<OAuthState>(FromBase64Url(payload));
        }
        catch (Exception ex) when (ex is JsonException or FormatException)
        {
            return null;
        }

        if (state is null || DateTimeOffset.UtcNow.ToUnixTimeSeconds() > state.ExpiresAtUnix)
            return null;

        // Single use: a replayed callback must not mint a second token. The nonce is remembered
        // only for the state's own lifetime, after which the expiry check above rejects it anyway.
        var cacheKey = $"oauth:state:{state.Nonce}";
        if (_cache.TryGetValue(cacheKey, out _)) return null;
        _cache.Set(cacheKey, true, Lifetime);

        return state;
    }

    private string Sign(string payload)
    {
        using var hmac = new HMACSHA256(_key);
        return Base64Url(hmac.ComputeHash(Encoding.UTF8.GetBytes(payload)));
    }

    public static string NewCodeVerifier()
    {
        var bytes = RandomNumberGenerator.GetBytes(32);
        return Base64Url(bytes);
    }

    /// The S256 challenge derived from a verifier, per RFC 7636.
    public static string CodeChallengeFor(string verifier)
    {
        var hash = SHA256.HashData(Encoding.ASCII.GetBytes(verifier));
        return Base64Url(hash);
    }

    private static string Base64Url(byte[] bytes) =>
        Convert.ToBase64String(bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private static byte[] FromBase64Url(string value)
    {
        var padded = value.Replace('-', '+').Replace('_', '/');
        padded = padded.PadRight(padded.Length + (4 - padded.Length % 4) % 4, '=');
        return Convert.FromBase64String(padded);
    }
}

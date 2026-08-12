using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.WebUtilities;

namespace DancePlatform.API.Services.ExternalAuth;

public class FacebookAuthProvider : IExternalAuthProvider
{
    private const string GraphVersion = "v21.0";
    private const string AuthorizeEndpoint = $"https://www.facebook.com/{GraphVersion}/dialog/oauth";
    private const string GraphBase = $"https://graph.facebook.com/{GraphVersion}";

    private readonly HttpClient _http;
    private readonly ILogger<FacebookAuthProvider> _log;
    private readonly string? _appId;
    private readonly string? _appSecret;

    public FacebookAuthProvider(HttpClient http, IConfiguration config, ILogger<FacebookAuthProvider> log)
    {
        _http = http;
        _log = log;
        _appId = config["Authentication:Facebook:AppId"];
        _appSecret = config["Authentication:Facebook:AppSecret"];
    }

    public string Name => "facebook";
    public string DisplayName => "Facebook";
    public bool IsConfigured => !string.IsNullOrWhiteSpace(_appId) && !string.IsNullOrWhiteSpace(_appSecret);

    public string BuildAuthorizeUrl(string redirectUri, string state, string codeChallenge)
    {
        var query = new Dictionary<string, string?>
        {
            ["client_id"] = _appId,
            ["redirect_uri"] = redirectUri,
            ["response_type"] = "code",
            // The two standard-access permissions. Anything beyond these drags the app into
            // Meta's App Review, so keep this list exactly this short.
            ["scope"] = "public_profile,email",
            ["state"] = state,
            ["code_challenge"] = codeChallenge,
            ["code_challenge_method"] = "S256"
        };
        return QueryHelpers.AddQueryString(AuthorizeEndpoint, query);
    }

    public async Task<ExternalIdentity?> ExchangeCodeAsync(
        string code, string redirectUri, string codeVerifier, CancellationToken ct)
    {
        var tokenUrl = QueryHelpers.AddQueryString($"{GraphBase}/oauth/access_token",
            new Dictionary<string, string?>
            {
                ["client_id"] = _appId,
                ["client_secret"] = _appSecret,
                ["redirect_uri"] = redirectUri,
                ["code"] = code,
                ["code_verifier"] = codeVerifier
            });

        var accessToken = await GetStringFieldAsync(tokenUrl, "access_token", ct);
        if (accessToken is null)
        {
            _log.LogWarning("Facebook token exchange returned no access_token");
            return null;
        }

        // Confirm the token was issued to *this* app before trusting anything it unlocks.
        // Facebook access tokens are bearer strings with no audience baked in, so without this
        // check someone could hand us a token minted for an unrelated Facebook app and log in
        // as whichever user it belongs to. /debug_token is the documented way to bind it.
        if (!await TokenBelongsToThisAppAsync(accessToken, ct))
        {
            _log.LogWarning("Facebook access token was not issued for this app — rejecting");
            return null;
        }

        var meUrl = QueryHelpers.AddQueryString($"{GraphBase}/me", new Dictionary<string, string?>
        {
            ["fields"] = "id,name,email,picture.type(large)",
            ["access_token"] = accessToken
        });

        using var response = await _http.GetAsync(meUrl, ct);
        if (!response.IsSuccessStatusCode)
        {
            _log.LogWarning("Facebook /me failed with {Status}", response.StatusCode);
            return null;
        }

        try
        {
            var root = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct)).RootElement;
            var subject = root.TryGetProperty("id", out var id) ? id.GetString() : null;
            if (string.IsNullOrEmpty(subject)) return null;

            // Email is absent whenever the user declines the permission or signed up to Facebook
            // with a phone number. That is expected, not an error — the account just has no email.
            var email = root.TryGetProperty("email", out var e) ? e.GetString() : null;
            var name = root.TryGetProperty("name", out var n) ? n.GetString() : null;

            string? avatar = null;
            if (root.TryGetProperty("picture", out var picture) &&
                picture.TryGetProperty("data", out var data) &&
                data.TryGetProperty("url", out var url))
                avatar = url.GetString();

            return new ExternalIdentity(subject, email, name, avatar);
        }
        catch (JsonException ex)
        {
            _log.LogWarning(ex, "Facebook /me returned unparseable JSON");
            return null;
        }
    }

    private async Task<bool> TokenBelongsToThisAppAsync(string accessToken, CancellationToken ct)
    {
        var url = QueryHelpers.AddQueryString($"{GraphBase}/debug_token", new Dictionary<string, string?>
        {
            ["input_token"] = accessToken,
            ["access_token"] = $"{_appId}|{_appSecret}"
        });

        using var response = await _http.GetAsync(url, ct);
        if (!response.IsSuccessStatusCode) return false;

        try
        {
            var root = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct)).RootElement;
            if (!root.TryGetProperty("data", out var data)) return false;

            var appId = data.TryGetProperty("app_id", out var a) ? a.GetString() : null;
            var isValid = data.TryGetProperty("is_valid", out var v) && v.GetBoolean();

            return isValid && string.Equals(appId, _appId, StringComparison.Ordinal);
        }
        catch (JsonException)
        {
            return false;
        }
    }

    /// Verifies and unpacks the `signed_request` Meta posts to the data-deletion callback,
    /// returning the Facebook user id it names. The HMAC check is the whole point: without it
    /// the endpoint would delete whichever account an anonymous caller asked it to.
    public string? ReadSignedRequestUserId(string? signedRequest)
    {
        if (string.IsNullOrEmpty(signedRequest) || !IsConfigured) return null;

        var parts = signedRequest.Split('.');
        if (parts.Length != 2) return null;

        try
        {
            var expected = HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(_appSecret!), Encoding.ASCII.GetBytes(parts[1]));

            if (!CryptographicOperations.FixedTimeEquals(FromBase64Url(parts[0]), expected))
                return null;

            var payload = JsonDocument.Parse(FromBase64Url(parts[1])).RootElement;
            return payload.TryGetProperty("user_id", out var id) ? id.GetString() : null;
        }
        catch (Exception ex) when (ex is JsonException or FormatException)
        {
            return null;
        }
    }

    private static byte[] FromBase64Url(string value)
    {
        var padded = value.Replace('-', '+').Replace('_', '/');
        padded = padded.PadRight(padded.Length + (4 - padded.Length % 4) % 4, '=');
        return Convert.FromBase64String(padded);
    }

    private async Task<string?> GetStringFieldAsync(string url, string field, CancellationToken ct)
    {
        using var response = await _http.GetAsync(url, ct);
        if (!response.IsSuccessStatusCode) return null;

        try
        {
            var root = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct)).RootElement;
            return root.TryGetProperty(field, out var el) ? el.GetString() : null;
        }
        catch (JsonException)
        {
            return null;
        }
    }
}

using System.Text.Json;
using Google.Apis.Auth;
using Microsoft.AspNetCore.WebUtilities;

namespace DancePlatform.API.Services.ExternalAuth;

public class GoogleAuthProvider : IExternalAuthProvider
{
    private const string AuthorizeEndpoint = "https://accounts.google.com/o/oauth2/v2/auth";
    private const string TokenEndpoint = "https://oauth2.googleapis.com/token";

    private readonly HttpClient _http;
    private readonly ILogger<GoogleAuthProvider> _log;
    private readonly string? _clientId;
    private readonly string? _clientSecret;

    public GoogleAuthProvider(HttpClient http, IConfiguration config, ILogger<GoogleAuthProvider> log)
    {
        _http = http;
        _log = log;
        _clientId = config["Authentication:Google:ClientId"];
        _clientSecret = config["Authentication:Google:ClientSecret"];
    }

    public string Name => "google";
    public string DisplayName => "Google";
    public bool IsConfigured => !string.IsNullOrWhiteSpace(_clientId) && !string.IsNullOrWhiteSpace(_clientSecret);

    public string BuildAuthorizeUrl(string redirectUri, string state, string codeChallenge)
    {
        var query = new Dictionary<string, string?>
        {
            ["client_id"] = _clientId,
            ["redirect_uri"] = redirectUri,
            ["response_type"] = "code",
            ["scope"] = "openid email profile",
            ["state"] = state,
            ["code_challenge"] = codeChallenge,
            ["code_challenge_method"] = "S256",
            // We only ever read the id_token at sign-in, so there is nothing to refresh offline.
            ["access_type"] = "online",
            // Without this, a browser signed into one Google account silently reuses it — bad on
            // a shared machine and impossible to recover from without visiting accounts.google.com.
            ["prompt"] = "select_account"
        };
        return QueryHelpers.AddQueryString(AuthorizeEndpoint, query);
    }

    public async Task<ExternalIdentity?> ExchangeCodeAsync(
        string code, string redirectUri, string codeVerifier, CancellationToken ct)
    {
        using var content = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["code"] = code,
            ["client_id"] = _clientId!,
            ["client_secret"] = _clientSecret!,
            ["redirect_uri"] = redirectUri,
            ["grant_type"] = "authorization_code",
            ["code_verifier"] = codeVerifier
        });

        using var response = await _http.PostAsync(TokenEndpoint, content, ct);
        if (!response.IsSuccessStatusCode)
        {
            _log.LogWarning("Google token exchange failed with {Status}", response.StatusCode);
            return null;
        }

        var body = await response.Content.ReadAsStringAsync(ct);
        string? idToken;
        try
        {
            idToken = JsonDocument.Parse(body).RootElement.TryGetProperty("id_token", out var el)
                ? el.GetString()
                : null;
        }
        catch (JsonException)
        {
            return null;
        }

        if (string.IsNullOrEmpty(idToken)) return null;

        GoogleJsonWebSignature.Payload payload;
        try
        {
            // Verifies the RS256 signature against Google's published JWKS and checks iss/exp.
            // Pinning Audience to our client id is the part that matters most: it rejects an
            // id_token minted for some other application, which would otherwise be a valid
            // Google token carrying an attacker-chosen subject.
            payload = await GoogleJsonWebSignature.ValidateAsync(idToken,
                new GoogleJsonWebSignature.ValidationSettings { Audience = new[] { _clientId! } });
        }
        catch (InvalidJwtException ex)
        {
            _log.LogWarning(ex, "Google id_token failed validation");
            return null;
        }

        return new ExternalIdentity(payload.Subject, payload.Email, payload.Name, payload.Picture);
    }
}

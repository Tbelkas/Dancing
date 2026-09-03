using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using DancePlatform.API.Models;
using DancePlatform.API.Services.ExternalAuth;
using Microsoft.IdentityModel.Tokens;

namespace DancePlatform.API.Services;

public interface ITokenService
{
    string CreateAccessToken(User user);

    /// A short-lived bearer for the gap between "signed in with Google" and "picked a username",
    /// during which no account exists yet.
    string CreateSignupTicket(string provider, ExternalIdentity identity);

    /// Returns null unless the ticket is intact, unexpired, and actually a signup ticket.
    (string Provider, ExternalIdentity Identity)? ReadSignupTicket(string ticket);
}

public class TokenService : ITokenService
{
    /// Deliberately NOT the API's normal audience. The JwtBearer handler validates against
    /// Jwt:Audience, so a signup ticket presented as an Authorization header is rejected before
    /// it reaches any [Authorize] endpoint — it can only ever be spent at /auth/external/complete.
    private const string SignupAudience = "DancePlatformSignup";
    private static readonly TimeSpan SignupTicketLifetime = TimeSpan.FromMinutes(15);

    private readonly IConfiguration _config;

    public TokenService(IConfiguration config) => _config = config;

    public string CreateAccessToken(User user)
    {
        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new Claim(ClaimTypes.Name, user.Username),
            // Admin is carried in the signed token so authorization needs no per-request DB
            // lookup. Trade-off: a grant/revoke only takes effect once the user gets a new
            // token (re-login), since the claim is fixed for the token's lifetime.
            new Claim("isAdmin", user.IsAdmin ? "true" : "false")
        };

        return Write(claims, _config["Jwt:Audience"],
            TimeSpan.FromDays(_config.GetValue("Jwt:ExpiryDays", 30)));
    }

    public string CreateSignupTicket(string provider, ExternalIdentity identity)
    {
        var claims = new List<Claim>
        {
            new("provider", provider),
            new("sub", identity.Subject)
        };
        if (!string.IsNullOrEmpty(identity.Email)) claims.Add(new Claim("email", identity.Email));
        if (!string.IsNullOrEmpty(identity.Name)) claims.Add(new Claim("name", identity.Name));
        if (!string.IsNullOrEmpty(identity.AvatarUrl)) claims.Add(new Claim("avatar", identity.AvatarUrl));

        return Write(claims, SignupAudience, SignupTicketLifetime);
    }

    public (string Provider, ExternalIdentity Identity)? ReadSignupTicket(string ticket)
    {
        var parameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = _config["Jwt:Issuer"],
            ValidAudience = SignupAudience,
            IssuerSigningKey = SigningKey(),
            ClockSkew = TimeSpan.FromSeconds(30)
        };

        try
        {
            var principal = new JwtSecurityTokenHandler().ValidateToken(ticket, parameters, out _);

            var provider = principal.FindFirst("provider")?.Value;
            // JwtSecurityTokenHandler maps "sub" onto NameIdentifier during validation, so read
            // both rather than depending on which mapping is in effect.
            var subject = principal.FindFirst("sub")?.Value
                          ?? principal.FindFirst(ClaimTypes.NameIdentifier)?.Value;
            if (string.IsNullOrEmpty(provider) || string.IsNullOrEmpty(subject)) return null;

            return (provider, new ExternalIdentity(
                subject,
                principal.FindFirst("email")?.Value,
                principal.FindFirst("name")?.Value,
                principal.FindFirst("avatar")?.Value));
        }
        catch (Exception ex) when (ex is SecurityTokenException or ArgumentException)
        {
            return null;
        }
    }

    private string Write(IEnumerable<Claim> claims, string? audience, TimeSpan lifetime)
    {
        var creds = new SigningCredentials(SigningKey(), SecurityAlgorithms.HmacSha256);
        var now = DateTime.UtcNow;
        // "iat" is stamped explicitly — this JwtSecurityToken constructor does not add one, and
        // revocation (UserTokenGuard) has nothing to compare against without it. A token with no
        // issue time can never be told apart from one minted before a password change.
        var withIssuedAt = claims.Append(new Claim(
            JwtRegisteredClaimNames.Iat,
            new DateTimeOffset(now).ToUnixTimeSeconds().ToString(),
            ClaimValueTypes.Integer64));

        var token = new JwtSecurityToken(
            issuer: _config["Jwt:Issuer"],
            audience: audience,
            claims: withIssuedAt,
            expires: now.Add(lifetime),
            signingCredentials: creds);

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    private SymmetricSecurityKey SigningKey() =>
        new(Encoding.UTF8.GetBytes(_config["Jwt:Key"]!));
}

using System.Security.Cryptography;
using System.Text;
using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Auth;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;

namespace DancePlatform.API.Services;

// CA1862 wants StringComparison.OrdinalIgnoreCase, but these comparisons run as EF Core LINQ that
// must translate to SQL LOWER() to hit the functional unique index — StringComparison isn't
// SQL-translatable here, so ToLower() is deliberate.
#pragma warning disable CA1862
public class AuthService : IAuthService
{
    /// Long enough that a person can act on the mail at their leisure, short enough that a link
    /// sitting in a mailbox isn't a standing key to the account.
    private static readonly TimeSpan ResetTokenLifetime = TimeSpan.FromHours(2);

    private readonly AppDbContext _db;
    private readonly ITokenService _tokens;
    private readonly IEmailSender _email;
    private readonly IConfiguration _config;
    private readonly IMemoryCache _cache;
    private readonly ILogger<AuthService> _log;

    public AuthService(AppDbContext db, ITokenService tokens, IEmailSender email,
                       IConfiguration config, IMemoryCache cache, ILogger<AuthService> log)
    {
        _db = db;
        _tokens = tokens;
        _email = email;
        _config = config;
        _cache = cache;
        _log = log;
    }

    public async Task<AuthResponse?> LoginAsync(LoginRequest request)
    {
        // Case-insensitive match (LOWER equality, not ILIKE — usernames can contain '_'/'%', which
        // ILIKE would treat as wildcards). Uses the functional unique index on LOWER("Username").
        var username = request.Username.ToLower();
        var user = await _db.Users.FirstOrDefaultAsync(u => u.Username.ToLower() == username);
        // An account created through Google/Facebook has no password hash. Reject it here rather
        // than handing an empty hash to BCrypt.Verify — that is the difference between "this
        // account has no password" and "any password might match".
        if (user is null || string.IsNullOrEmpty(user.PasswordHash))
            return null;
        if (!BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            return null;

        return Authenticated(user);
    }

    public async Task<(RegisterResult, AuthResponse?)> RegisterAsync(RegisterRequest request)
    {
        // Reject a name already taken in any casing — "Justas" and "justas" are one account.
        var username = request.Username.ToLower();
        if (await _db.Users.AnyAsync(u => u.Username.ToLower() == username))
            return (RegisterResult.UsernameTaken, null);

        var email = request.Email.Trim().ToLower();
        if (await _db.Users.AnyAsync(u => u.Email != null && u.Email.ToLower() == email))
            return (RegisterResult.EmailTaken, null);

        var user = new User
        {
            Username = request.Username,
            Email = email,
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.Password),
            Name = request.Name,
            Nickname = request.Nickname
        };

        _db.Users.Add(user);
        try
        {
            await _db.SaveChangesAsync();
        }
        catch (DbUpdateException)
        {
            // Lost a race against a concurrent registration of the same name or address (one of
            // the functional unique indexes rejected the insert) — surface it as "taken" rather
            // than a 500. Which of the two it was doesn't change what the user has to do next.
            return (RegisterResult.UsernameTaken, null);
        }

        return (RegisterResult.Ok, Authenticated(user));
    }

    public async Task RequestPasswordResetAsync(string email, CancellationToken ct = default)
    {
        var normalized = email.Trim().ToLower();
        var user = await _db.Users.FirstOrDefaultAsync(
            u => u.Email != null && u.Email.ToLower() == normalized, ct);
        if (user is null)
        {
            // Deliberately silent. The endpoint answers 202 for every address; anything else
            // visible to the caller would turn this into a way to test who has an account here.
            _log.LogInformation("Password reset requested for an address with no account.");
            return;
        }

        // Any link already in flight stops working. Otherwise asking for a reset *because* an
        // old link might have been seen would leave that old link working.
        var outstanding = await _db.PasswordResetTokens
            .Where(t => t.UserId == user.Id && t.UsedAt == null)
            .ToListAsync(ct);
        foreach (var old in outstanding) old.UsedAt = DateTime.UtcNow;

        var token = NewToken();
        _db.PasswordResetTokens.Add(new PasswordResetToken
        {
            UserId = user.Id,
            TokenHash = Hash(token),
            ExpiresAt = DateTime.UtcNow.Add(ResetTokenLifetime)
        });
        await _db.SaveChangesAsync(ct);

        // App:UiUrl is only *required* to be set when a social provider is configured (see
        // Program.cs), and social sign-in is dormant — so fall back to Cors:Origin, which
        // production must already have right or the SPA could not call the API at all. Without
        // this fallback every reset mail from the Pi would link to localhost.
        var uiUrl = (_config["App:UiUrl"] is { Length: > 0 } configured && !configured.Contains("localhost", StringComparison.OrdinalIgnoreCase)
            ? configured
            : _config["Cors:Origin"] ?? _config["App:UiUrl"] ?? "http://localhost:4200").TrimEnd('/');
        var link = $"{uiUrl}/reset-password?token={Uri.EscapeDataString(token)}";
        var who = string.IsNullOrWhiteSpace(user.Nickname) ? user.Name : user.Nickname;
        var body =
            $"Hi {who},\n\n" +
            $"Someone asked to reset the password for your Dance Platform account ({user.Username}).\n" +
            $"Open this link within {ResetTokenLifetime.TotalHours:0} hours to choose a new one:\n\n" +
            $"{link}\n\n" +
            "If it wasn't you, ignore this message — nothing has changed, and the link can only be used once.\n";

        await _email.SendAsync(user.Email!, "Reset your Dance Platform password", body, ct);
    }

    public async Task<AuthResponse?> ResetPasswordAsync(ResetPasswordRequest request)
    {
        var hash = Hash(request.Token);
        var now = DateTime.UtcNow;
        var token = await _db.PasswordResetTokens
            .Include(t => t.User)
            .FirstOrDefaultAsync(t => t.TokenHash == hash && t.UsedAt == null && t.ExpiresAt > now);
        if (token is null) return null;

        token.UsedAt = now;
        token.User.PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.NewPassword);
        // Whoever knew the old password is signed out everywhere. Without this, a reset would
        // leave them holding a working token for up to another 30 days — the owner would have
        // locked their own door from the inside.
        token.User.TokensValidFrom = now;
        await _db.SaveChangesAsync();
        // Drop the cached cutoff so the old tokens die now rather than at the end of the
        // guard's cache window — the whole point of a reset is that it takes effect at once.
        UserTokenGuard.Forget(_cache, token.UserId);

        return Authenticated(token.User);
    }

    public async Task<(PasswordChangeResult, AuthResponse?)> ChangePasswordAsync(
        int userId, ChangePasswordRequest request)
    {
        var user = await _db.Users.FindAsync(userId);
        if (user is null) return (PasswordChangeResult.UserNotFound, null);

        // An account created through a provider has no password to confirm — this is how it
        // gains one. An account that has one has to prove it knows it.
        if (!string.IsNullOrEmpty(user.PasswordHash) &&
            !BCrypt.Net.BCrypt.Verify(request.CurrentPassword, user.PasswordHash))
            return (PasswordChangeResult.WrongCurrentPassword, null);

        user.PasswordHash = BCrypt.Net.BCrypt.HashPassword(request.NewPassword);
        user.TokensValidFrom = DateTime.UtcNow;
        await _db.SaveChangesAsync();
        UserTokenGuard.Forget(_cache, user.Id);

        // Issued after TokensValidFrom is set, so the caller's replacement token survives the
        // invalidation that just retired every other one — including the token they asked with.
        return (PasswordChangeResult.Ok, Authenticated(user));
    }

    private AuthResponse Authenticated(User user) => new()
    {
        Token = _tokens.CreateAccessToken(user),
        Username = user.Username,
        UserId = user.Id
    };

    /// 256 bits from the CSPRNG, URL-safe so it survives being pasted out of a mail client.
    private static string NewToken() => Base64Url(RandomNumberGenerator.GetBytes(32));

    private static string Hash(string token) =>
        Base64Url(SHA256.HashData(Encoding.UTF8.GetBytes(token)));

    private static string Base64Url(byte[] bytes) =>
        Convert.ToBase64String(bytes).Replace('+', '-').Replace('/', '_').TrimEnd('=');
}
#pragma warning restore CA1862

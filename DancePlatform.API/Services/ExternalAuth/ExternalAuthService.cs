using System.Text;
using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Auth;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services.ExternalAuth;

public enum LinkResult { Linked, AlreadyLinkedToYou, TakenByAnotherAccount }
public enum UnlinkResult { Unlinked, NotLinked, WouldLockOut }

public interface IExternalAuthService
{
    IReadOnlyList<ExternalProviderDto> ConfiguredProviders();
    IExternalAuthProvider? Find(string name);

    /// The account already linked to this provider identity, or null if we've never seen it.
    Task<User?> FindUserAsync(string provider, string subject, CancellationToken ct);

    Task<SignupTicketDto> DescribeTicketAsync(string provider, ExternalIdentity identity, CancellationToken ct);
    Task<AuthResponse?> CompleteSignupAsync(string provider, ExternalIdentity identity, string username, CancellationToken ct);

    Task<LinkResult> LinkAsync(int userId, string provider, ExternalIdentity identity, CancellationToken ct);
    Task<UnlinkResult> UnlinkAsync(int userId, string provider, CancellationToken ct);

    /// Unlink without the lock-out guard, for a provider-initiated data-deletion request —
    /// that has to be honoured even when it leaves the account with no way to sign in.
    Task ForceUnlinkAsync(int userId, string provider, CancellationToken ct);
    Task<LinkedAccountsDto> GetLinkedAccountsAsync(int userId, CancellationToken ct);
}

#pragma warning disable CA1862 // ToLower() is deliberate — see AuthService for why.
public class ExternalAuthService : IExternalAuthService
{
    private readonly AppDbContext _db;
    private readonly ITokenService _tokens;
    private readonly IReadOnlyList<IExternalAuthProvider> _providers;

    public ExternalAuthService(AppDbContext db, ITokenService tokens, IEnumerable<IExternalAuthProvider> providers)
    {
        _db = db;
        _tokens = tokens;
        _providers = providers.ToList();
    }

    public IReadOnlyList<ExternalProviderDto> ConfiguredProviders() =>
        _providers.Where(p => p.IsConfigured)
                  .Select(p => new ExternalProviderDto(p.Name, p.DisplayName))
                  .ToList();

    /// Only ever resolves a provider that has credentials, so an unconfigured provider name is
    /// indistinguishable from an unknown one (a 404 either way).
    public IExternalAuthProvider? Find(string name) =>
        _providers.FirstOrDefault(p =>
            p.IsConfigured && string.Equals(p.Name, name, StringComparison.OrdinalIgnoreCase));

    public async Task<User?> FindUserAsync(string provider, string subject, CancellationToken ct)
    {
        var login = await _db.UserLogins
            .Include(l => l.User)
            .FirstOrDefaultAsync(l => l.Provider == provider && l.ProviderUserId == subject, ct);
        return login?.User;
    }

    public async Task<SignupTicketDto> DescribeTicketAsync(
        string provider, ExternalIdentity identity, CancellationToken ct) =>
        new(provider, identity.Email, identity.Name,
            await SuggestUsernameAsync(identity, ct));

    public async Task<AuthResponse?> CompleteSignupAsync(
        string provider, ExternalIdentity identity, string username, CancellationToken ct)
    {
        var lowered = username.ToLower();
        if (await _db.Users.AnyAsync(u => u.Username.ToLower() == lowered, ct))
            return null;

        var user = new User
        {
            Username = username,
            // No password: this account is reachable only through its provider. AuthService
            // refuses to run BCrypt against an empty hash, so the password form can't touch it.
            PasswordHash = string.Empty,
            Email = identity.Email,
            Name = identity.Name ?? username,
            Nickname = string.Empty,
            AvatarUrl = identity.AvatarUrl
        };
        user.Logins.Add(new UserLogin
        {
            Provider = provider,
            ProviderUserId = identity.Subject,
            Email = identity.Email
        });

        _db.Users.Add(user);
        try
        {
            await _db.SaveChangesAsync(ct);
        }
        catch (DbUpdateException)
        {
            // Lost a race — either the username or the (provider, subject) pair was claimed
            // between the check above and the insert. Both unique indexes surface here.
            return null;
        }

        return new AuthResponse
        {
            Token = _tokens.CreateAccessToken(user),
            Username = user.Username,
            UserId = user.Id
        };
    }

    public async Task<LinkResult> LinkAsync(
        int userId, string provider, ExternalIdentity identity, CancellationToken ct)
    {
        var existing = await _db.UserLogins
            .FirstOrDefaultAsync(l => l.Provider == provider && l.ProviderUserId == identity.Subject, ct);

        if (existing is not null)
            return existing.UserId == userId ? LinkResult.AlreadyLinkedToYou : LinkResult.TakenByAnotherAccount;

        _db.UserLogins.Add(new UserLogin
        {
            UserId = userId,
            Provider = provider,
            ProviderUserId = identity.Subject,
            Email = identity.Email
        });

        // Backfill the address for accounts that predate the Email column, but never overwrite
        // one the user already has.
        var user = await _db.Users.FirstAsync(u => u.Id == userId, ct);
        if (string.IsNullOrEmpty(user.Email) && !string.IsNullOrEmpty(identity.Email))
            user.Email = identity.Email;

        try
        {
            await _db.SaveChangesAsync(ct);
        }
        catch (DbUpdateException)
        {
            return LinkResult.TakenByAnotherAccount;
        }

        return LinkResult.Linked;
    }

    public async Task<UnlinkResult> UnlinkAsync(int userId, string provider, CancellationToken ct)
    {
        var login = await _db.UserLogins
            .FirstOrDefaultAsync(l => l.UserId == userId && l.Provider == provider, ct);
        if (login is null) return UnlinkResult.NotLinked;

        // Removing the only way into an account orphans it — there is no password reset to fall
        // back on. Refuse, and let the UI explain instead of stranding the user.
        var user = await _db.Users.FirstAsync(u => u.Id == userId, ct);
        var otherLogins = await _db.UserLogins.CountAsync(l => l.UserId == userId && l.Id != login.Id, ct);
        if (otherLogins == 0 && string.IsNullOrEmpty(user.PasswordHash))
            return UnlinkResult.WouldLockOut;

        _db.UserLogins.Remove(login);
        await _db.SaveChangesAsync(ct);
        return UnlinkResult.Unlinked;
    }

    public async Task ForceUnlinkAsync(int userId, string provider, CancellationToken ct)
    {
        var login = await _db.UserLogins
            .FirstOrDefaultAsync(l => l.UserId == userId && l.Provider == provider, ct);
        if (login is null) return;

        _db.UserLogins.Remove(login);

        // The address came from the provider being deleted, so it goes too.
        var user = await _db.Users.FirstAsync(u => u.Id == userId, ct);
        if (!string.IsNullOrEmpty(login.Email) &&
            string.Equals(user.Email, login.Email, StringComparison.OrdinalIgnoreCase))
            user.Email = null;

        await _db.SaveChangesAsync(ct);
    }

    public async Task<LinkedAccountsDto> GetLinkedAccountsAsync(int userId, CancellationToken ct)
    {
        var logins = await _db.UserLogins
            .Where(l => l.UserId == userId)
            .OrderBy(l => l.CreatedAt)
            .ToListAsync(ct);

        var hasPassword = await _db.Users
            .Where(u => u.Id == userId)
            .Select(u => u.PasswordHash != "")
            .FirstOrDefaultAsync(ct);

        var accounts = logins.Select(l => new LinkedAccountDto(
            l.Provider,
            _providers.FirstOrDefault(p => p.Name == l.Provider)?.DisplayName ?? l.Provider,
            l.Email,
            l.CreatedAt)).ToList();

        return new LinkedAccountsDto(accounts, hasPassword);
    }

    /// A username the user is likely to accept, derived from their email local part (or name).
    /// Only a suggestion — the signup screen lets them replace it before anything is created.
    private async Task<string> SuggestUsernameAsync(ExternalIdentity identity, CancellationToken ct)
    {
        var seed = identity.Email?.Split('@')[0] ?? identity.Name ?? "dancer";
        var basis = Sanitize(seed);
        if (basis.Length < 3) basis = "dancer";
        if (basis.Length > 20) basis = basis[..20];

        if (!await ExistsAsync(basis, ct)) return basis;

        // Fall back to a numeric suffix, then to a random one — a popular local part like
        // "info" or "hello" can plausibly collide past a handful of tries.
        for (var i = 2; i <= 20; i++)
        {
            var candidate = $"{basis}{i}";
            if (!await ExistsAsync(candidate, ct)) return candidate;
        }

        return $"{basis}{Random.Shared.Next(1000, 9999)}";
    }

    private Task<bool> ExistsAsync(string username, CancellationToken ct)
    {
        var lowered = username.ToLower();
        return _db.Users.AnyAsync(u => u.Username.ToLower() == lowered, ct);
    }

    private static string Sanitize(string value)
    {
        var sb = new StringBuilder(value.Length);
        foreach (var c in value.ToLowerInvariant())
        {
            if (char.IsAsciiLetterOrDigit(c)) sb.Append(c);
            else if ((c == '.' || c == '-' || c == '_') && sb.Length > 0) sb.Append('_');
        }
        return sb.ToString().Trim('_');
    }
}
#pragma warning restore CA1862

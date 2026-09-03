using DancePlatform.API.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;

namespace DancePlatform.API.Services;

public interface IUserTokenGuard
{
    /// <summary>
    /// True unless the account has retired tokens issued at or before <paramref name="issuedAtUtc"/>
    /// (a password change, a reset, or a deletion). Unknown users answer false — the account is
    /// gone, and so is anything signed for it.
    /// </summary>
    Task<bool> IsCurrentAsync(int userId, DateTime issuedAtUtc);
}

/// <summary>
/// The revocation half of a stateless token scheme. Access tokens live 30 days and carry
/// everything they need, which is what makes them cheap — and what makes a password reset
/// meaningless without this check.
///
/// The cutoff is cached briefly so this doesn't put a database round-trip on every single
/// authenticated request to a Raspberry Pi. The cost of the cache is the width of the window
/// in which a just-retired token still works; a minute is a fair trade against a query per
/// request, and the endpoints that retire tokens drop the entry themselves so the common
/// case ("I changed my password, sign my other devices out") is immediate anyway.
/// </summary>
public class UserTokenGuard : IUserTokenGuard
{
    private static readonly TimeSpan CacheLifetime = TimeSpan.FromMinutes(1);

    private readonly AppDbContext _db;
    private readonly IMemoryCache _cache;

    public UserTokenGuard(AppDbContext db, IMemoryCache cache)
    {
        _db = db;
        _cache = cache;
    }

    public static string CacheKey(int userId) => $"tokens-valid-from:{userId}";

    /// <summary>Called by whatever just retired this user's tokens, so the change lands now
    /// rather than at the end of the cache window.</summary>
    public static void Forget(IMemoryCache cache, int userId) => cache.Remove(CacheKey(userId));

    public async Task<bool> IsCurrentAsync(int userId, DateTime issuedAtUtc)
    {
        if (!_cache.TryGetValue<Cutoff>(CacheKey(userId), out var cutoff) || cutoff is null)
        {
            var row = await _db.Users
                .AsNoTracking()
                .Where(u => u.Id == userId)
                .Select(u => new { u.TokensValidFrom })
                .FirstOrDefaultAsync();

            // A missing row is cached too: an authenticated request for a deleted account
            // shouldn't re-query on every retry.
            cutoff = new Cutoff(row is not null, row?.TokensValidFrom);
            _cache.Set(CacheKey(userId), cutoff,
                new MemoryCacheEntryOptions { AbsoluteExpirationRelativeToNow = CacheLifetime });
        }

        if (!cutoff.UserExists) return false;
        if (cutoff.ValidFrom is null) return true;

        // "iat" is whole seconds, so both sides are floored before comparing: a token minted in
        // the same second as the cutoff (the replacement handed back by /auth/change-password)
        // must pass, while any token from an earlier second must not.
        return Floor(issuedAtUtc) >= Floor(cutoff.ValidFrom.Value);
    }

    private static DateTime Floor(DateTime value) =>
        new(value.Ticks - (value.Ticks % TimeSpan.TicksPerSecond), value.Kind);

    private sealed record Cutoff(bool UserExists, DateTime? ValidFrom);
}

using Microsoft.Extensions.Caching.Memory;

namespace DancePlatform.API.Services;

public interface ILoginThrottle
{
    /// <summary>True when this caller has burned through its failed attempts and must wait.</summary>
    bool IsLockedOut(string ipKey, string username);

    void RecordFailure(string ipKey, string username);

    /// <summary>A correct password clears the counters — a person who finally remembers it
    /// shouldn't stay locked out behind their own typos.</summary>
    void RecordSuccess(string ipKey, string username);
}

/// <summary>
/// Counts *failed* sign-ins, which is the thing worth limiting: the fixed-window limiter in
/// front of /auth/login can only see volume, and any volume limit tight enough to stop a
/// dictionary run would also lock out a shared address full of legitimate users.
///
/// Two counters, both of which must stay under the threshold:
///   • per address — stops one machine working through a password list;
///   • per username — stops a distributed run converging on one account.
/// The username counter is the reason this is not purely IP-based; the address counter is the
/// reason someone can't lock a stranger out of their account by targeting it (an attacker
/// tripping the username counter is the same thing as protecting it, and the window is short).
///
/// In-memory on purpose: this is a single-instance API on a Pi, and a restart clearing the
/// counters is an acceptable trade for having no extra table on the SD card.
/// </summary>
public class LoginThrottle : ILoginThrottle
{
    public const int MaxFailures = 8;
    public static readonly TimeSpan Window = TimeSpan.FromMinutes(15);

    private readonly IMemoryCache _cache;

    public LoginThrottle(IMemoryCache cache) => _cache = cache;

    public bool IsLockedOut(string ipKey, string username) =>
        Failures(IpKey(ipKey)) >= MaxFailures || Failures(UserKey(username)) >= MaxFailures;

    public void RecordFailure(string ipKey, string username)
    {
        Bump(IpKey(ipKey));
        Bump(UserKey(username));
    }

    public void RecordSuccess(string ipKey, string username)
    {
        _cache.Remove(IpKey(ipKey));
        _cache.Remove(UserKey(username));
    }

    private int Failures(string key) => _cache.TryGetValue<int>(key, out var count) ? count : 0;

    private void Bump(string key)
    {
        // Sliding would let a slow drip of guesses run forever; the window is absolute, so a
        // locked-out caller always gets a fresh budget at a predictable time.
        var count = Failures(key) + 1;
        _cache.Set(key, count, new MemoryCacheEntryOptions { AbsoluteExpirationRelativeToNow = Window });
    }

    private static string IpKey(string ipKey) => $"login-fail:ip:{ipKey}";

    // Case-insensitive, to match the case-insensitive account lookup in AuthService — otherwise
    // varying the casing would mint a fresh budget for the same account.
    private static string UserKey(string username) => $"login-fail:user:{username.ToLowerInvariant()}";
}

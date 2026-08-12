using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Auth;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

// CA1862 wants StringComparison.OrdinalIgnoreCase, but these comparisons run as EF Core LINQ that
// must translate to SQL LOWER() to hit the functional unique index — StringComparison isn't
// SQL-translatable here, so ToLower() is deliberate.
#pragma warning disable CA1862
public class AuthService : IAuthService
{
    private readonly AppDbContext _db;
    private readonly ITokenService _tokens;

    public AuthService(AppDbContext db, ITokenService tokens)
    {
        _db = db;
        _tokens = tokens;
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

        return new AuthResponse
        {
            Token = _tokens.CreateAccessToken(user),
            Username = user.Username,
            UserId = user.Id
        };
    }

    public async Task<AuthResponse?> RegisterAsync(RegisterRequest request)
    {
        // Reject a name already taken in any casing — "Justas" and "justas" are one account.
        var username = request.Username.ToLower();
        if (await _db.Users.AnyAsync(u => u.Username.ToLower() == username))
            return null;

        var user = new User
        {
            Username = request.Username,
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
            // Lost a race against a concurrent registration of the same name (the functional unique
            // index rejected the insert) — surface it as "taken" rather than a 500.
            return null;
        }

        return new AuthResponse
        {
            Token = _tokens.CreateAccessToken(user),
            Username = user.Username,
            UserId = user.Id
        };
    }

}
#pragma warning restore CA1862

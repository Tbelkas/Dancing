using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Auth;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

namespace DancePlatform.API.Services;

// CA1862 wants StringComparison.OrdinalIgnoreCase, but these comparisons run as EF Core LINQ that
// must translate to SQL LOWER() to hit the functional unique index — StringComparison isn't
// SQL-translatable here, so ToLower() is deliberate.
#pragma warning disable CA1862
public class AuthService : IAuthService
{
    private readonly AppDbContext _db;
    private readonly IConfiguration _config;

    public AuthService(AppDbContext db, IConfiguration config)
    {
        _db = db;
        _config = config;
    }

    public async Task<AuthResponse?> LoginAsync(LoginRequest request)
    {
        // Case-insensitive match (LOWER equality, not ILIKE — usernames can contain '_'/'%', which
        // ILIKE would treat as wildcards). Uses the functional unique index on LOWER("Username").
        var username = request.Username.ToLower();
        var user = await _db.Users.FirstOrDefaultAsync(u => u.Username.ToLower() == username);
        if (user is null || !BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            return null;

        return new AuthResponse
        {
            Token = GenerateToken(user),
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
            Token = GenerateToken(user),
            Username = user.Username,
            UserId = user.Id
        };
    }

    private string GenerateToken(User user)
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_config["Jwt:Key"]!));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new Claim(ClaimTypes.Name, user.Username),
            // Admin is carried in the signed token so authorization needs no per-request DB
            // lookup. Trade-off: a grant/revoke only takes effect once the user gets a new
            // token (re-login), since the claim is fixed for the token's lifetime.
            new Claim("isAdmin", user.IsAdmin ? "true" : "false")
        };

        var token = new JwtSecurityToken(
            issuer: _config["Jwt:Issuer"],
            audience: _config["Jwt:Audience"],
            claims: claims,
            expires: DateTime.UtcNow.AddDays(_config.GetValue("Jwt:ExpiryDays", 30)),
            signingCredentials: creds);

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
#pragma warning restore CA1862

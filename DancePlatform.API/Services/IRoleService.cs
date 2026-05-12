namespace DancePlatform.API.Services;

/// <summary>
/// Abstracts role resolution. Currently reads IsAdmin from the database.
/// Future: swap to read the "IsAdmin" claim from the JWT token — update
/// RegisterAsync in AuthService to embed the claim, then change the
/// implementation here to call user.FindFirstValue("IsAdmin") instead.
/// </summary>
public interface IRoleService
{
    Task<bool> IsAdminAsync(int userId);
}

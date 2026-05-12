using DancePlatform.API.Data;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class RoleService : IRoleService
{
    private readonly AppDbContext _db;

    public RoleService(AppDbContext db) => _db = db;

    public async Task<bool> IsAdminAsync(int userId) =>
        await _db.Users.Where(u => u.Id == userId).Select(u => u.IsAdmin).FirstOrDefaultAsync();
}

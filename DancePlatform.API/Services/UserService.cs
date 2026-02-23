using DancePlatform.API.Data;
using DancePlatform.API.DTOs.User;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class UserService : IUserService
{
    private readonly AppDbContext _db;

    public UserService(AppDbContext db) => _db = db;

    public async Task<UserProfileDto?> GetProfileAsync(int userId) =>
        await _db.Users
            .Include(u => u.FavoriteDances).ThenInclude(f => f.Dance)
            .Include(u => u.LearnedDances).ThenInclude(l => l.Dance)
            .Where(u => u.Id == userId)
            .Select(u => new UserProfileDto
            {
                Id = u.Id,
                Username = u.Username,
                Name = u.Name,
                Nickname = u.Nickname,
                AvatarUrl = u.AvatarUrl,
                Visibility = u.Visibility.ToString(),
                DateAdded = u.DateAdded,
                FavoriteDances = u.FavoriteDances.Select(f => f.Dance.Name).ToList(),
                LearnedDances = u.LearnedDances.Select(l => l.Dance.Name).ToList()
            }).FirstOrDefaultAsync();

    public async Task<UserProfileDto?> UpdateProfileAsync(int userId, UpdateProfileRequest request)
    {
        var user = await _db.Users.FindAsync(userId);
        if (user is null) return null;

        if (request.Name is not null) user.Name = request.Name;
        if (request.Nickname is not null) user.Nickname = request.Nickname;
        if (request.AvatarUrl is not null) user.AvatarUrl = request.AvatarUrl;
        if (request.Visibility is not null &&
            Enum.TryParse<Models.ProfileVisibility>(request.Visibility, out var vis))
            user.Visibility = vis;

        await _db.SaveChangesAsync();
        return await GetProfileAsync(userId);
    }
}

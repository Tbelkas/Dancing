using DancePlatform.API.Data;
using DancePlatform.API.DTOs.User;
using DancePlatform.API.Models;
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
                FavoriteDances = u.FavoriteDances.Select(f => new DanceRef(f.Dance.Id, f.Dance.Name)).ToList(),
                LearnedDances = u.LearnedDances.Select(l => new DanceRef(l.Dance.Id, l.Dance.Name)).ToList()
            }).FirstOrDefaultAsync();

    public async Task<UserProfileDto?> UpdateProfileAsync(int userId, UpdateProfileRequest request)
    {
        var user = await _db.Users.FindAsync(userId);
        if (user is null) return null;

        if (request.Name is not null) user.Name = request.Name;
        if (request.Nickname is not null) user.Nickname = request.Nickname;
        if (request.AvatarUrl is not null) user.AvatarUrl = request.AvatarUrl;
        if (request.Visibility is not null &&
            Enum.TryParse<ProfileVisibility>(request.Visibility, out var vis))
            user.Visibility = vis;

        await _db.SaveChangesAsync();
        return await GetProfileAsync(userId);
    }

    public async Task<PublicProfileDto?> GetPublicProfileAsync(string username) =>
        await _db.Users
            .Include(u => u.LearnedDances).ThenInclude(l => l.Dance)
            .Where(u => u.Username == username && u.Visibility == ProfileVisibility.Public)
            .Select(u => new PublicProfileDto
            {
                Id = u.Id,
                Username = u.Username,
                Nickname = u.Nickname,
                AvatarUrl = u.AvatarUrl,
                LearnedDances = u.LearnedDances.Select(l => new DanceRef(l.Dance.Id, l.Dance.Name)).ToList()
            })
            .FirstOrDefaultAsync();

    public async Task<List<MyStyleWithDancesDto>> GetMyDancesAsync(int userId)
    {
        var user = await _db.Users
            .Include(u => u.MyStyles)
                .ThenInclude(ms => ms.Style)
                    .ThenInclude(s => s.DanceStyles)
                        .ThenInclude(ds => ds.Dance)
            .Include(u => u.LearnedDances)
            .Include(u => u.InProgressDances)
            .FirstOrDefaultAsync(u => u.Id == userId);

        if (user is null) return new();

        var learnedIds = user.LearnedDances.Select(l => l.DanceId).ToHashSet();
        var inProgressIds = user.InProgressDances.Select(ip => ip.DanceId).ToHashSet();

        return user.MyStyles
            .OrderBy(ms => ms.Style.Name)
            .Select(ms => new MyStyleWithDancesDto
            {
                StyleId = ms.StyleId,
                StyleName = ms.Style.Name,
                Dances = ms.Style.DanceStyles
                    .Select(ds => ds.Dance)
                    .Where(d => learnedIds.Contains(d.Id) || inProgressIds.Contains(d.Id))
                    .OrderBy(d => d.Name)
                    .Select(d => new MyDanceItemDto
                    {
                        Id = d.Id,
                        Name = d.Name,
                        Status = learnedIds.Contains(d.Id) ? "learned" : "inProgress"
                    })
                    .ToList()
            })
            .ToList();
    }
}

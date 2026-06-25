using DancePlatform.API.Data;
using DancePlatform.API.DTOs.User;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class UserService : IUserService
{
    private readonly AppDbContext _db;

    public UserService(AppDbContext db) => _db = db;

    /// <summary>Maps a dance entity (with its styles loaded) to a link-ready reference.</summary>
    private static DanceRef ToRef(Dance d) => new(d.Id, d.Name, d.Slug, SlugGenerator.StyleSlug(d));

    public async Task<UserProfileDto?> GetProfileAsync(int userId)
    {
        var user = await _db.Users
            .Include(u => u.FavoriteDances).ThenInclude(f => f.Dance).ThenInclude(d => d.DanceStyles).ThenInclude(ds => ds.Style)
            .Include(u => u.LearnedDances).ThenInclude(l => l.Dance).ThenInclude(d => d.DanceStyles).ThenInclude(ds => ds.Style)
            .Include(u => u.InProgressDances).ThenInclude(ip => ip.Dance).ThenInclude(d => d.DanceStyles).ThenInclude(ds => ds.Style)
            .FirstOrDefaultAsync(u => u.Id == userId);
        if (user is null) return null;

        return new UserProfileDto
        {
            Id = user.Id,
            Username = user.Username,
            Name = user.Name,
            Nickname = user.Nickname,
            AvatarUrl = user.AvatarUrl,
            Visibility = user.Visibility.ToString(),
            DateAdded = user.DateAdded,
            FavoriteDances = user.FavoriteDances.Select(f => ToRef(f.Dance)).ToList(),
            LearnedDances = user.LearnedDances.Select(l => ToRef(l.Dance)).ToList(),
            InProgressDances = user.InProgressDances.Select(ip => ToRef(ip.Dance)).ToList()
        };
    }

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

    public async Task<PublicProfileDto?> GetPublicProfileAsync(string username)
    {
        var user = await _db.Users
            .Include(u => u.LearnedDances).ThenInclude(l => l.Dance).ThenInclude(d => d.DanceStyles).ThenInclude(ds => ds.Style)
            .FirstOrDefaultAsync(u => u.Username == username && u.Visibility == ProfileVisibility.Public);
        if (user is null) return null;

        return new PublicProfileDto
        {
            Id = user.Id,
            Username = user.Username,
            Nickname = user.Nickname,
            AvatarUrl = user.AvatarUrl,
            LearnedDances = user.LearnedDances.Select(l => ToRef(l.Dance)).ToList()
        };
    }

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
                        Slug = d.Slug,
                        // Link under the style tab the dance is shown in.
                        StyleSlug = SlugGenerator.Slugify(ms.Style.Name),
                        Status = learnedIds.Contains(d.Id) ? "learned" : "inProgress"
                    })
                    .ToList()
            })
            .ToList();
    }
}

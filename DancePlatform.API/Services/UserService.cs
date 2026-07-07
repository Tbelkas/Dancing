using DancePlatform.API.Data;
using DancePlatform.API.DTOs.User;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class UserService : IUserService
{
    private readonly AppDbContext _db;

    public UserService(AppDbContext db) => _db = db;

    /// <summary>
    /// Projects dances to link-ready refs entirely in SQL. The canonical style *name* (lowest StyleId)
    /// is pulled in the query and slugified in memory afterwards, since SlugGenerator can't run inside
    /// EF — the same split DanceService.ProjectRows/ToDto uses. This is what lets the profile queries
    /// skip loading the full Dance → DanceStyles → Style graph (a cartesian fetch across three
    /// collection Includes) and materialise only the four columns a DanceRef actually needs.
    /// </summary>
    private static IQueryable<DanceRefRow> ProjectRefs(IQueryable<Dance> source) =>
        source.Select(d => new DanceRefRow
        {
            Id = d.Id,
            Name = d.Name,
            Slug = d.Slug,
            CanonicalStyleName = d.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault()
        });

    private static DanceRef ToRef(DanceRefRow r) =>
        new(r.Id, r.Name, r.Slug, r.CanonicalStyleName is null ? string.Empty : SlugGenerator.Slugify(r.CanonicalStyleName));

    public async Task<UserProfileDto?> GetProfileAsync(int userId)
    {
        // Scalar profile fields only — no dance graph pulled onto the tracked User.
        var user = await _db.Users.AsNoTracking()
            .Where(u => u.Id == userId)
            .Select(u => new { u.Id, u.Username, u.Name, u.Nickname, u.AvatarUrl, u.Visibility, u.DateAdded })
            .FirstOrDefaultAsync();
        if (user is null) return null;

        // Each list is its own lean projection straight off the join table, so favorites/learned/
        // in-progress no longer multiply into a cartesian fetch the way stacked collection Includes did.
        var favorites = await ProjectRefs(_db.UserFavoriteDances.Where(f => f.UserId == userId).Select(f => f.Dance)).AsNoTracking().ToListAsync();
        var learned = await ProjectRefs(_db.UserLearnedDances.Where(l => l.UserId == userId).Select(l => l.Dance)).AsNoTracking().ToListAsync();
        var inProgress = await ProjectRefs(_db.UserInProgressDances.Where(ip => ip.UserId == userId).Select(ip => ip.Dance)).AsNoTracking().ToListAsync();

        return new UserProfileDto
        {
            Id = user.Id,
            Username = user.Username,
            Name = user.Name,
            Nickname = user.Nickname,
            AvatarUrl = user.AvatarUrl,
            Visibility = user.Visibility.ToString(),
            DateAdded = user.DateAdded,
            FavoriteDances = favorites.Select(ToRef).ToList(),
            LearnedDances = learned.Select(ToRef).ToList(),
            InProgressDances = inProgress.Select(ToRef).ToList()
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
        var user = await _db.Users.AsNoTracking()
            .Where(u => u.Username == username && u.Visibility == ProfileVisibility.Public)
            .Select(u => new { u.Id, u.Username, u.Nickname, u.AvatarUrl })
            .FirstOrDefaultAsync();
        if (user is null) return null;

        var learned = await ProjectRefs(_db.UserLearnedDances.Where(l => l.UserId == user.Id).Select(l => l.Dance)).AsNoTracking().ToListAsync();

        return new PublicProfileDto
        {
            Id = user.Id,
            Username = user.Username,
            Nickname = user.Nickname,
            AvatarUrl = user.AvatarUrl,
            LearnedDances = learned.Select(ToRef).ToList()
        };
    }

    public async Task<List<MyStyleWithDancesDto>> GetMyDancesAsync(int userId)
    {
        // The user's followed styles — every one is returned (even with zero matching dances), so the
        // list of tabs is stable. Ordered by name in memory to match the previous behaviour exactly.
        var myStyles = (await _db.UserMyStyles.AsNoTracking()
                .Where(ms => ms.UserId == userId)
                .Select(ms => new { ms.StyleId, ms.Style.Name })
                .ToListAsync())
            .OrderBy(ms => ms.Name)
            .ToList();
        if (myStyles.Count == 0) return new();

        var styleIds = myStyles.Select(ms => ms.StyleId).ToList();

        // The old query loaded EVERY dance of every followed style (a "General"-style follow ≈ the whole
        // 697-dance catalog) as tracked entities and filtered to learned/in-progress in memory. Here the
        // filter runs IN the database: we materialise one (styleId, dance) row only for the dances the
        // user has actually learned or is practicing, within their followed styles. A dance in several
        // followed styles yields one row per style, so it still appears under each style tab — matching
        // the original that walked ms.Style.DanceStyles per style.
        var rows = await _db.DanceStyles.AsNoTracking()
            .Where(ds => styleIds.Contains(ds.StyleId)
                && (ds.Dance.LearnedBy.Any(l => l.UserId == userId) || ds.Dance.InProgressBy.Any(ip => ip.UserId == userId)))
            .Select(ds => new
            {
                ds.StyleId,
                DanceId = ds.DanceId,
                ds.Dance.Name,
                ds.Dance.Slug,
                IsLearned = ds.Dance.LearnedBy.Any(l => l.UserId == userId)
            })
            .ToListAsync();

        var byStyle = rows.ToLookup(r => r.StyleId);

        return myStyles
            .Select(ms => new MyStyleWithDancesDto
            {
                StyleId = ms.StyleId,
                StyleName = ms.Name,
                Dances = byStyle[ms.StyleId]
                    .OrderBy(r => r.Name)
                    .Select(r => new MyDanceItemDto
                    {
                        Id = r.DanceId,
                        Name = r.Name,
                        Slug = r.Slug,
                        // Link under the style tab the dance is shown in.
                        StyleSlug = SlugGenerator.Slugify(ms.Name),
                        // Learned wins over in-progress when somehow both are set (mirrors the old precedence).
                        Status = r.IsLearned ? "learned" : "inProgress"
                    })
                    .ToList()
            })
            .ToList();
    }

    // In-SQL projection target for a DanceRef; the style slug is computed in memory (SlugGenerator
    // can't translate to SQL), so we carry the canonical style *name* and slugify after materializing.
    private sealed class DanceRefRow
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Slug { get; set; } = string.Empty;
        public string? CanonicalStyleName { get; set; }
    }
}

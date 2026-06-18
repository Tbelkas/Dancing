using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class DanceService : IDanceService
{
    private readonly AppDbContext _db;

    public DanceService(AppDbContext db) => _db = db;

    public async Task<List<DanceDto>> GetAllAsync(int? userId) =>
        (await BuildEntityQuery().ToListAsync()).Select(d => ToDto(d, userId)).ToList();

    public async Task<DanceDto?> GetByIdAsync(int id, int? userId)
    {
        var dance = await BuildEntityQuery().FirstOrDefaultAsync(d => d.Id == id);
        return dance is null ? null : ToDto(dance, userId);
    }

    public async Task<DanceDto?> GetBySlugAsync(string slug, int? userId)
    {
        var dance = await BuildEntityQuery().FirstOrDefaultAsync(d => d.Slug == slug);
        return dance is null ? null : ToDto(dance, userId);
    }

    /// <summary>Slugifies the name; appends -2, -3, ... when another dance already uses the slug.</summary>
    public async Task<string> GenerateUniqueSlugAsync(string name, int? excludeDanceId = null)
    {
        var baseSlug = SlugGenerator.Slugify(name);
        var slug = baseSlug;
        for (var i = 2; await _db.Dances.AnyAsync(d => d.Slug == slug && d.Id != excludeDanceId); i++)
            slug = $"{baseSlug}-{i}";
        return slug;
    }

    public async Task<DanceDto> CreateAsync(CreateDanceRequest request)
    {
        if (!Enum.TryParse<DifficultyLevel>(request.Difficulty, true, out var difficulty))
            difficulty = DifficultyLevel.None;

        var dance = new Dance
        {
            Name = request.Name,
            Slug = await GenerateUniqueSlugAsync(request.Name),
            Description = request.Description,
            Difficulty = difficulty
        };
        _db.Dances.Add(dance);
        await _db.SaveChangesAsync();

        foreach (var styleId in request.StyleIds)
            _db.DanceStyles.Add(new DanceStyle { DanceId = dance.Id, StyleId = styleId });

        foreach (var musicalStyleId in request.MusicalStyleIds)
            _db.DanceMusicalStyles.Add(new DanceMusicalStyle { DanceId = dance.Id, MusicalStyleId = musicalStyleId });

        foreach (var instructorId in request.InstructorIds)
            _db.DanceInstructors.Add(new DanceInstructor { DanceId = dance.Id, InstructorId = instructorId });

        await _db.SaveChangesAsync();
        return (await GetByIdAsync(dance.Id, null))!;
    }

    public async Task<DanceDto?> UpdateAsync(int id, UpdateDanceRequest request)
    {
        var dance = await _db.Dances
            .Include(d => d.DanceStyles)
            .Include(d => d.DanceMusicalStyles)
            .Include(d => d.DanceInstructors)
            .FirstOrDefaultAsync(d => d.Id == id);
        if (dance is null) return null;

        if (request.Name is not null && request.Name != dance.Name)
        {
            dance.Name = request.Name;
            dance.Slug = await GenerateUniqueSlugAsync(request.Name, dance.Id);
        }
        if (request.Description is not null) dance.Description = request.Description;
        if (request.Difficulty is not null && Enum.TryParse<DifficultyLevel>(request.Difficulty, true, out var diff))
            dance.Difficulty = diff;

        if (request.StyleIds is not null)
        {
            _db.DanceStyles.RemoveRange(dance.DanceStyles);
            foreach (var styleId in request.StyleIds)
                _db.DanceStyles.Add(new DanceStyle { DanceId = dance.Id, StyleId = styleId });
        }

        if (request.MusicalStyleIds is not null)
        {
            _db.DanceMusicalStyles.RemoveRange(dance.DanceMusicalStyles);
            foreach (var musicalStyleId in request.MusicalStyleIds)
                _db.DanceMusicalStyles.Add(new DanceMusicalStyle { DanceId = dance.Id, MusicalStyleId = musicalStyleId });
        }

        if (request.InstructorIds is not null)
        {
            _db.DanceInstructors.RemoveRange(dance.DanceInstructors);
            foreach (var instructorId in request.InstructorIds)
                _db.DanceInstructors.Add(new DanceInstructor { DanceId = dance.Id, InstructorId = instructorId });
        }

        await _db.SaveChangesAsync();
        return await GetByIdAsync(id, null);
    }

    public async Task<bool> DeleteAsync(int id)
    {
        var dance = await _db.Dances.FindAsync(id);
        if (dance is null) return false;
        _db.Dances.Remove(dance);
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ToggleFavoriteAsync(int userId, int danceId)
    {
        var existing = await _db.UserFavoriteDances.FindAsync(userId, danceId);
        if (existing is not null)
        {
            _db.UserFavoriteDances.Remove(existing);
            await _db.SaveChangesAsync();
            return false;
        }
        _db.UserFavoriteDances.Add(new UserFavoriteDance { UserId = userId, DanceId = danceId });
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ToggleLearnedAsync(int userId, int danceId)
    {
        var existing = await _db.UserLearnedDances.FindAsync(userId, danceId);
        if (existing is not null)
        {
            _db.UserLearnedDances.Remove(existing);
            await _db.SaveChangesAsync();
            return false;
        }
        _db.UserLearnedDances.Add(new UserLearnedDance { UserId = userId, DanceId = danceId });
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ToggleInProgressAsync(int userId, int danceId)
    {
        var existing = await _db.UserInProgressDances.FindAsync(userId, danceId);
        if (existing is not null)
        {
            _db.UserInProgressDances.Remove(existing);
            await _db.SaveChangesAsync();
            return false;
        }
        _db.UserInProgressDances.Add(new UserInProgressDance { UserId = userId, DanceId = danceId });
        await _db.SaveChangesAsync();
        return true;
    }

    /// <summary>
    /// Sets the mutually-exclusive learning status (notstarted/inprogress/learned) for a user+dance
    /// in a single transaction. Reconciles both join tables together so the two states can never
    /// both be set — enforcing the invariant server-side rather than trusting the client.
    /// </summary>
    public async Task<DanceStatusDto> SetStatusAsync(int userId, int danceId, string status)
    {
        var learned = await _db.UserLearnedDances.FindAsync(userId, danceId);
        var inProgress = await _db.UserInProgressDances.FindAsync(userId, danceId);

        var wantLearned = status == "learned";
        var wantInProgress = status == "inprogress";

        if (wantLearned && learned is null)
            _db.UserLearnedDances.Add(new UserLearnedDance { UserId = userId, DanceId = danceId });
        else if (!wantLearned && learned is not null)
            _db.UserLearnedDances.Remove(learned);

        if (wantInProgress && inProgress is null)
            _db.UserInProgressDances.Add(new UserInProgressDance { UserId = userId, DanceId = danceId });
        else if (!wantInProgress && inProgress is not null)
            _db.UserInProgressDances.Remove(inProgress);

        await _db.SaveChangesAsync();
        return new DanceStatusDto(wantLearned, wantInProgress);
    }

    public async Task<DanceDto?> RateDanceAsync(int userId, int danceId, int rating)
    {
        var existing = await _db.DanceRatings.FindAsync(userId, danceId);
        if (existing is not null)
            existing.Rating = rating;
        else
            _db.DanceRatings.Add(new DanceRating { UserId = userId, DanceId = danceId, Rating = rating });

        await _db.SaveChangesAsync();
        return await GetByIdAsync(danceId, userId);
    }

    public async Task<SearchDancesResult> SearchAsync(string query, int? styleId, int? musicalStyleId, string? difficulty, string? status, string? sortBy, int? userId, int page = 1, int pageSize = 24)
    {
        var entityQ = BuildEntityQuery().AsQueryable();

        if (!string.IsNullOrWhiteSpace(query))
            entityQ = entityQ.Where(d => d.Name.ToLower().Contains(query.ToLower()));

        if (styleId.HasValue)
            entityQ = entityQ.Where(d => d.DanceStyles.Any(ds => ds.StyleId == styleId.Value));

        if (musicalStyleId.HasValue)
            entityQ = entityQ.Where(d => d.DanceMusicalStyles.Any(dms => dms.MusicalStyleId == musicalStyleId.Value));

        if (!string.IsNullOrWhiteSpace(difficulty) && Enum.TryParse<DifficultyLevel>(difficulty, true, out var diffLevel))
            entityQ = entityQ.Where(d => d.Difficulty == diffLevel);

        if (!string.IsNullOrWhiteSpace(status) && userId.HasValue)
        {
            entityQ = status.ToLower() switch
            {
                "favorite"   => entityQ.Where(d => d.FavoritedBy.Any(f => f.UserId == userId.Value)),
                "learned"    => entityQ.Where(d => d.LearnedBy.Any(l => l.UserId == userId.Value)),
                "inprogress" => entityQ.Where(d => d.InProgressBy.Any(ip => ip.UserId == userId.Value)),
                "notstarted" => entityQ.Where(d =>
                    !d.LearnedBy.Any(l => l.UserId == userId.Value) &&
                    !d.InProgressBy.Any(ip => ip.UserId == userId.Value)),
                _ => entityQ
            };
        }

        var clampedPage = Math.Max(1, page);

        // Sorts that can be translated to SQL: push ORDER BY + SKIP/TAKE to the database.
        if (sortBy is null or "name" or "newest")
        {
            var total = await entityQ.CountAsync();
            var sortedQ = sortBy == "newest"
                ? entityQ.OrderByDescending(d => d.DateAdded)
                : entityQ.OrderBy(d => d.Name);
            var items = (await sortedQ.Skip((clampedPage - 1) * pageSize).Take(pageSize).ToListAsync())
                .Select(d => ToDto(d, userId)).ToList();
            return new SearchDancesResult { Items = items, Total = total, Page = clampedPage, PageSize = pageSize };
        }

        // Sorts on computed aggregates (rating average, favorite count) must happen in memory.
        var all = (await entityQ.ToListAsync()).Select(d => ToDto(d, userId)).ToList();
        var sorted = sortBy == "rating"
            ? all.OrderByDescending(d => d.AverageRating).ThenByDescending(d => d.RatingCount).ToList()
            : all.OrderByDescending(d => d.FavoriteCount).ToList(); // "popular"
        return new SearchDancesResult
        {
            Items = sorted.Skip((clampedPage - 1) * pageSize).Take(pageSize).ToList(),
            Total = sorted.Count,
            Page = clampedPage,
            PageSize = pageSize
        };
    }

    private IQueryable<Dance> BuildEntityQuery() =>
        _db.Dances
            .Include(d => d.DanceStyles).ThenInclude(ds => ds.Style)
            .Include(d => d.DanceMusicalStyles).ThenInclude(dms => dms.MusicalStyle)
            .Include(d => d.DanceInstructors).ThenInclude(di => di.Instructor)
            .Include(d => d.Videos)
            .Include(d => d.FavoritedBy)
            .Include(d => d.LearnedBy)
            .Include(d => d.InProgressBy)
            .Include(d => d.Ratings);

    private static DanceDto ToDto(Dance d, int? userId) => new()
    {
        Id = d.Id,
        Name = d.Name,
        Slug = d.Slug,
        Description = d.Description,
        DateAdded = d.DateAdded,
        Difficulty = d.Difficulty.ToString(),
        Styles = d.DanceStyles.Select(ds => ds.Style.Name).ToList(),
        MusicalStyles = d.DanceMusicalStyles.Select(dms => dms.MusicalStyle.Name).ToList(),
        Instructors = d.DanceInstructors.Select(di => di.Instructor.Name).ToList(),
        VideoCount = d.Videos.Count,
        ThumbnailVideoId = d.Videos.OrderBy(v => v.DateAdded).Select(v => v.VideoId).FirstOrDefault(),
        ThumbnailPlatform = d.Videos.OrderBy(v => v.DateAdded).Select(v => v.Platform).FirstOrDefault(),
        FavoriteCount = d.FavoritedBy.Count,
        LearnedCount = d.LearnedBy.Count,
        AverageRating = d.Ratings.Count > 0 ? d.Ratings.Average(r => r.Rating) : 0,
        RatingCount = d.Ratings.Count,
        UserRating = userId.HasValue
            ? d.Ratings.FirstOrDefault(r => r.UserId == userId.Value)?.Rating
            : null,
        IsFavorite = userId.HasValue && d.FavoritedBy.Any(f => f.UserId == userId.Value),
        IsLearned = userId.HasValue && d.LearnedBy.Any(l => l.UserId == userId.Value),
        IsInProgress = userId.HasValue && d.InProgressBy.Any(ip => ip.UserId == userId.Value)
    };
}

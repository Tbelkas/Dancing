using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class DanceService : IDanceService
{
    private readonly AppDbContext _db;

    public DanceService(AppDbContext db) => _db = db;

    public async Task<List<DanceNameDto>> GetNamesAsync() =>
        await _db.Dances.OrderBy(d => d.Name).Select(d => new DanceNameDto { Id = d.Id, Name = d.Name }).ToListAsync();

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

    /// <summary>
    /// Resolves /dances/{styleSlug}/{danceSlug}. Dance slugs are unique per style, so the style
    /// segment is what disambiguates same-named steps across styles. Falls back to a plain slug
    /// match if the style segment doesn't resolve, so legacy single-segment links still work.
    /// </summary>
    public async Task<DanceDto?> GetByStyleAndSlugAsync(string styleSlug, string danceSlug, int? userId)
    {
        var styleId = await ResolveStyleIdAsync(styleSlug);
        var query = BuildEntityQuery().Where(d => d.Slug == danceSlug);
        if (styleId is not null)
            query = query.Where(d => d.DanceStyles.Any(ds => ds.StyleId == styleId));
        var dance = await query.FirstOrDefaultAsync();
        return dance is null ? null : ToDto(dance, userId);
    }

    /// <summary>Maps a style slug back to its id by slugifying style names in memory (the set is tiny).</summary>
    private async Task<int?> ResolveStyleIdAsync(string styleSlug)
    {
        var styles = await _db.Styles.Select(s => new { s.Id, s.Name }).ToListAsync();
        return styles.FirstOrDefault(s => SlugGenerator.Slugify(s.Name) == styleSlug)?.Id;
    }

    /// <summary>
    /// "More like this" — other dances that share at least one style (the dance's "type") and have a
    /// playable video. Ranked: same difficulty first, then most-favorited, then best-rated.
    /// </summary>
    public async Task<List<DanceDto>> GetRecommendedAsync(int id, int? userId, int limit = 8)
    {
        var styleIds = await _db.DanceStyles
            .Where(ds => ds.DanceId == id)
            .Select(ds => ds.StyleId)
            .ToListAsync();
        if (styleIds.Count == 0) return new List<DanceDto>();

        var difficulty = await _db.Dances.Where(d => d.Id == id)
            .Select(d => d.Difficulty).FirstOrDefaultAsync();

        var recs = await BuildEntityQuery()
            .Where(d => d.Id != id
                     && d.Videos.Any()
                     && d.DanceStyles.Any(ds => styleIds.Contains(ds.StyleId)))
            .OrderByDescending(d => d.Difficulty == difficulty)
            .ThenByDescending(d => d.FavoriteCount)
            .ThenByDescending(d => d.AverageRating)
            .ThenByDescending(d => d.DateAdded)
            .Take(limit)
            .ToListAsync();

        return recs.Select(d => ToDto(d, userId)).ToList();
    }

    /// <summary>
    /// Slugifies the name, appending -2, -3, ... only when another dance <em>sharing one of the same
    /// styles</em> already uses that slug. Slugs are therefore unique per style, so the same step name
    /// in two different styles can keep the same clean slug (disambiguated by the style URL segment).
    /// </summary>
    public async Task<string> GenerateUniqueSlugAsync(string name, IEnumerable<int> styleIds, int? excludeDanceId = null)
    {
        var styleIdList = styleIds.ToList();
        var baseSlug = SlugGenerator.Slugify(name);
        var slug = baseSlug;
        for (var i = 2; await _db.Dances.AnyAsync(d =>
                 d.Slug == slug
                 && d.Id != excludeDanceId
                 && d.DanceStyles.Any(ds => styleIdList.Contains(ds.StyleId))); i++)
            slug = $"{baseSlug}-{i}";
        return slug;
    }

    /// <summary>
    /// Recomputes every dance's slug under the per-style uniqueness rule, in Id order, collapsing
    /// the legacy global -2/-3 suffixes that were only needed because slugs used to be globally
    /// unique. Idempotent. Returns the number of slugs that changed. Admin-only, run once.
    /// </summary>
    public async Task<int> ReslugAllAsync()
    {
        var dances = await _db.Dances
            .Include(d => d.DanceStyles)
            .OrderBy(d => d.Id)
            .ToListAsync();

        // (styleId, slug) pairs already taken — a slug may repeat across styles but not within one.
        var taken = new HashSet<(int StyleId, string Slug)>();
        var changed = 0;

        foreach (var dance in dances)
        {
            var styleIds = dance.DanceStyles.Select(ds => ds.StyleId).DefaultIfEmpty(0).ToList();
            var baseSlug = SlugGenerator.Slugify(dance.Name);
            var slug = baseSlug;
            for (var i = 2; styleIds.Any(sid => taken.Contains((sid, slug))); i++)
                slug = $"{baseSlug}-{i}";

            foreach (var sid in styleIds) taken.Add((sid, slug));
            if (dance.Slug != slug) { dance.Slug = slug; changed++; }
        }

        if (changed > 0) await _db.SaveChangesAsync();
        return changed;
    }

    public async Task<DanceDto> CreateAsync(CreateDanceRequest request)
    {
        if (!Enum.TryParse<DifficultyLevel>(request.Difficulty, true, out var difficulty))
            difficulty = DifficultyLevel.None;

        var dance = new Dance
        {
            Name = request.Name,
            Slug = await GenerateUniqueSlugAsync(request.Name, request.StyleIds),
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

        // Use the incoming styles if the update sets them, otherwise the dance's current styles —
        // slug uniqueness is scoped to whichever styles the dance will end up in.
        var slugStyleIds = request.StyleIds ?? dance.DanceStyles.Select(ds => ds.StyleId).ToList();
        if (request.Name is not null && request.Name != dance.Name)
        {
            dance.Name = request.Name;
            dance.Slug = await GenerateUniqueSlugAsync(request.Name, slugStyleIds, dance.Id);
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
        var isFavorite = existing is null;
        if (existing is not null)
            _db.UserFavoriteDances.Remove(existing);
        else
            _db.UserFavoriteDances.Add(new UserFavoriteDance { UserId = userId, DanceId = danceId });
        await _db.SaveChangesAsync();
        await _db.Dances.Where(d => d.Id == danceId)
            .ExecuteUpdateAsync(s => s.SetProperty(d => d.FavoriteCount, d => d.FavoriteCount + (isFavorite ? 1 : -1)));
        return isFavorite;
    }

    public async Task<bool> ToggleLearnedAsync(int userId, int danceId)
    {
        var existing = await _db.UserLearnedDances.FindAsync(userId, danceId);
        var isLearned = existing is null;
        if (existing is not null)
            _db.UserLearnedDances.Remove(existing);
        else
            _db.UserLearnedDances.Add(new UserLearnedDance { UserId = userId, DanceId = danceId });
        await _db.SaveChangesAsync();
        await _db.Dances.Where(d => d.Id == danceId)
            .ExecuteUpdateAsync(s => s.SetProperty(d => d.LearnedCount, d => d.LearnedCount + (isLearned ? 1 : -1)));
        return isLearned;
    }

    public async Task<bool> ToggleInProgressAsync(int userId, int danceId)
    {
        var existing = await _db.UserInProgressDances.FindAsync(userId, danceId);
        var isInProgress = existing is null;
        if (existing is not null)
            _db.UserInProgressDances.Remove(existing);
        else
            _db.UserInProgressDances.Add(new UserInProgressDance { UserId = userId, DanceId = danceId });
        await _db.SaveChangesAsync();
        return isInProgress;
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

        var learnedDelta = (wantLearned ? 1 : 0) - (learned is not null ? 1 : 0);

        if (wantLearned && learned is null)
            _db.UserLearnedDances.Add(new UserLearnedDance { UserId = userId, DanceId = danceId });
        else if (!wantLearned && learned is not null)
            _db.UserLearnedDances.Remove(learned);

        if (wantInProgress && inProgress is null)
            _db.UserInProgressDances.Add(new UserInProgressDance { UserId = userId, DanceId = danceId });
        else if (!wantInProgress && inProgress is not null)
            _db.UserInProgressDances.Remove(inProgress);

        await _db.SaveChangesAsync();

        if (learnedDelta != 0)
            await _db.Dances.Where(d => d.Id == danceId)
                .ExecuteUpdateAsync(s => s.SetProperty(d => d.LearnedCount, d => d.LearnedCount + learnedDelta));

        return new DanceStatusDto(wantLearned, wantInProgress);
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

        // Sorts push ORDER BY + COUNT + SKIP/TAKE to the database. "recommended"/"tutorials" rank on
        // video shape via EXISTS/COUNT subqueries: a full-length tutorial (VideoType "tutorial" with no
        // StartTime clip window) is the signal for "extensive teaching content", as opposed to a short
        // clip or a slice carved out of a many-dance compilation (which always carries StartTime).
        IQueryable<Dance> orderedQ = sortBy switch
        {
            "recommended" => entityQ
                .OrderByDescending(d => d.Videos.Any(v => v.VideoType == "tutorial" && v.StartTime == null))
                .ThenByDescending(d => d.Videos.Any(v => v.VideoType == "tutorial"))
                .ThenByDescending(d => d.AverageRating)
                .ThenByDescending(d => d.FavoriteCount)
                .ThenBy(d => d.Name),
            "tutorials" => entityQ
                .OrderByDescending(d => d.Videos.Count(v => v.VideoType == "tutorial" && v.StartTime == null))
                .ThenByDescending(d => d.Videos.Count(v => v.VideoType == "tutorial"))
                .ThenByDescending(d => d.AverageRating)
                .ThenBy(d => d.Name),
            "rating"  => entityQ.OrderByDescending(d => d.AverageRating).ThenByDescending(d => d.RatingCount),
            "popular" => entityQ.OrderByDescending(d => d.FavoriteCount),
            "newest"  => entityQ.OrderByDescending(d => d.DateAdded),
            _         => entityQ.OrderBy(d => d.Name)
        };

        var total = await entityQ.CountAsync();
        var items = (await orderedQ.Skip((clampedPage - 1) * pageSize).Take(pageSize).ToListAsync())
            .Select(d => ToDto(d, userId)).ToList();

        return new SearchDancesResult { Items = items, Total = total, Page = clampedPage, PageSize = pageSize };
    }

    private IQueryable<Dance> BuildEntityQuery() =>
        _db.Dances
            .Include(d => d.DanceStyles).ThenInclude(ds => ds.Style)
            .Include(d => d.DanceMusicalStyles).ThenInclude(dms => dms.MusicalStyle)
            .Include(d => d.DanceInstructors).ThenInclude(di => di.Instructor)
            .Include(d => d.Videos)
            .Include(d => d.FavoritedBy)
            .Include(d => d.LearnedBy)
            .Include(d => d.InProgressBy);

    private static DanceDto ToDto(Dance d, int? userId)
    {
        var thumb = d.Videos.OrderBy(v => v.DateAdded).FirstOrDefault();
        return new DanceDto
        {
            Id = d.Id,
            Name = d.Name,
            Slug = d.Slug,
            StyleSlug = SlugGenerator.StyleSlug(d),
            Description = d.Description,
            DateAdded = d.DateAdded,
            Difficulty = d.Difficulty.ToString(),
            Styles = d.DanceStyles.Select(ds => ds.Style.Name).ToList(),
            MusicalStyles = d.DanceMusicalStyles.Select(dms => dms.MusicalStyle.Name).ToList(),
            Instructors = d.DanceInstructors.Select(di => di.Instructor.Name).ToList(),
            VideoCount = d.Videos.Count,
            ThumbnailVideoId = thumb?.VideoId,
            ThumbnailPlatform = thumb?.Platform,
            FavoriteCount = d.FavoriteCount,
            LearnedCount = d.LearnedCount,
            AverageRating = d.AverageRating,
            RatingCount = d.RatingCount,
            IsFavorite = userId.HasValue && d.FavoritedBy.Any(f => f.UserId == userId.Value),
            IsLearned = userId.HasValue && d.LearnedBy.Any(l => l.UserId == userId.Value),
            IsInProgress = userId.HasValue && d.InProgressBy.Any(ip => ip.UserId == userId.Value)
        };
    }
}

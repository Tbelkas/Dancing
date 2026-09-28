using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Glossary;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class GlossaryService : IGlossaryService
{
    private readonly AppDbContext _db;

    public GlossaryService(AppDbContext db) => _db = db;

    public async Task<List<GlossarySummaryDto>> GetAllAsync(int? userId)
    {
        var uid = userId ?? 0;
        var rows = await _db.GlossaryTerms
            .GroupBy(t => new { t.StyleId, t.Style.Name })
            .Select(g => new
            {
                g.Key.StyleId,
                g.Key.Name,
                TermCount = g.Count(),
                MoveCount = g.Count(t => t.IsLearnable),
                LearnedCount = g.Count(t => t.IsLearnable && t.LearnedBy.Any(l => l.UserId == uid))
            })
            .ToListAsync();

        return rows
            .OrderBy(r => r.Name)
            .Select(r => new GlossarySummaryDto
            {
                StyleId = r.StyleId,
                StyleName = r.Name,
                StyleSlug = SlugGenerator.Slugify(r.Name),
                TermCount = r.TermCount,
                MoveCount = r.MoveCount,
                LearnedCount = r.LearnedCount
            })
            .ToList();
    }

    public async Task<GlossaryDto?> GetByStyleAsync(string styleSlug, int? userId)
    {
        // Style slugs aren't stored — they're derived from the name — so resolve in memory over
        // the few dozen styles rather than trying to express Slugify in SQL.
        var styles = await _db.Styles.Select(s => new { s.Id, s.Name }).ToListAsync();
        var style = styles.FirstOrDefault(s => string.Equals(SlugGenerator.Slugify(s.Name), styleSlug, StringComparison.OrdinalIgnoreCase));
        if (style is null) return null;

        var uid = userId ?? 0;
        var terms = await _db.GlossaryTerms
            .Where(t => t.StyleId == style.Id)
            .OrderBy(t => t.SortOrder)
            .Select(t => new
            {
                t.Id, t.Slug, t.Name, t.Aliases, t.Category, t.Summary, t.Description,
                t.Steps, t.Tips, t.Related, t.Difficulty, t.IsLearnable,
                IsLearned = t.LearnedBy.Any(l => l.UserId == uid),
                Dance = t.Dance == null ? null : new
                {
                    t.Dance.Id,
                    t.Dance.Slug,
                    CanonicalStyleName = t.Dance.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault(),
                    // Global videos only: the glossary is the same page for everyone.
                    VideoCount = t.Dance.Videos.Count(v => v.OwnerUserId == null),
                    Thumb = t.Dance.Videos
                        .Where(v => v.OwnerUserId == null)
                        .OrderByDescending(v => v.AverageRating).ThenBy(v => v.DateAdded)
                        .Select(v => new { v.VideoId, v.Platform })
                        .FirstOrDefault()
                }
            })
            .ToListAsync();

        if (terms.Count == 0) return null;

        var names = terms.ToDictionary(t => t.Slug, t => t.Name);

        var dto = new GlossaryDto
        {
            StyleId = style.Id,
            StyleName = style.Name,
            StyleSlug = SlugGenerator.Slugify(style.Name),
            TermCount = terms.Count,
            MoveCount = terms.Count(t => t.IsLearnable),
            LearnedCount = terms.Count(t => t.IsLearnable && t.IsLearned)
        };

        // Categories keep the order their first term was authored in.
        foreach (var group in terms.GroupBy(t => t.Category))
        {
            dto.Categories.Add(new GlossaryCategoryDto
            {
                Name = group.Key,
                Terms = group.Select(t => new GlossaryTermDto
                {
                    Id = t.Id,
                    Slug = t.Slug,
                    Name = t.Name,
                    Aliases = t.Aliases,
                    Summary = t.Summary,
                    Description = t.Description,
                    Steps = t.Steps,
                    Tips = t.Tips,
                    Related = t.Related
                        .Where(r => r != t.Slug && names.ContainsKey(r))
                        .Select(r => new GlossaryRefDto { Slug = r, Name = names[r] })
                        .ToList(),
                    Difficulty = t.Difficulty.ToString(),
                    IsLearnable = t.IsLearnable,
                    IsLearned = t.IsLearnable && t.IsLearned,
                    // A dance whose videos are all quarantined or gone has nothing to show.
                    Dance = t.Dance is null || t.Dance.VideoCount == 0 ? null : new GlossaryDanceDto
                    {
                        Id = t.Dance.Id,
                        Slug = t.Dance.Slug,
                        StyleSlug = t.Dance.CanonicalStyleName is null ? string.Empty : SlugGenerator.Slugify(t.Dance.CanonicalStyleName),
                        VideoCount = t.Dance.VideoCount,
                        ThumbnailVideoId = t.Dance.Thumb?.VideoId,
                        ThumbnailPlatform = t.Dance.Thumb?.Platform
                    }
                }).ToList()
            });
        }

        return dto;
    }

    public async Task<bool> SetLearnedAsync(int userId, int termId, bool learned)
    {
        var learnable = await _db.GlossaryTerms.AnyAsync(t => t.Id == termId && t.IsLearnable);
        if (!learnable) return false;

        var existing = await _db.UserLearnedGlossaryTerms.FindAsync(userId, termId);
        if (learned && existing is null)
            _db.UserLearnedGlossaryTerms.Add(new UserLearnedGlossaryTerm { UserId = userId, GlossaryTermId = termId });
        else if (!learned && existing is not null)
            _db.UserLearnedGlossaryTerms.Remove(existing);
        else
            return true;

        try
        {
            await _db.SaveChangesAsync();
        }
        catch (DbUpdateException) when (learned)
        {
            // A double-click raced the insert; the row the other request wrote is the one we wanted.
        }
        return true;
    }
}

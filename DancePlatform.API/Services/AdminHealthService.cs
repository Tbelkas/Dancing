using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Admin;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class AdminHealthService : IAdminHealthService
{
    private readonly AppDbContext _db;

    public AdminHealthService(AppDbContext db) => _db = db;

    /// <summary>
    /// How many examples each check carries back. A sample, not the set: the count is the number
    /// that matters, and shipping 400 rows of "no description" would make the page slower than the
    /// scripts it replaces without making anyone likelier to fix one.
    /// </summary>
    private const int SampleSize = 25;

    public async Task<CatalogHealthDto> GetAsync()
    {
        // Dance carries no global filter (only Video does), so "in the catalogue" has to be said
        // out loud here every time.
        var approvedDances = _db.Dances.Where(d => d.ReviewState == "approved");

        var health = new CatalogHealthDto
        {
            Totals = new CatalogTotalsDto
            {
                Dances = await approvedDances.CountAsync(),
                Videos = await _db.Videos.CountAsync(v => v.OwnerUserId == null),
                PendingVideos = await _db.Videos.IgnoreQueryFilters()
                    .CountAsync(v => v.ReviewState == "pending" && v.OwnerUserId == null),
                RejectedVideos = await _db.Videos.IgnoreQueryFilters()
                    .CountAsync(v => v.ReviewState == "rejected" && v.OwnerUserId == null),
                PendingDances = await _db.Dances.CountAsync(d => d.ReviewState == "pending"),
                OpenFlags = await _db.VideoFlags.CountAsync(f => f.ResolvedAt == null),
                Styles = await _db.Styles.CountAsync(),
                Instructors = await _db.Instructors.CountAsync()
            }
        };

        // --- Dance-shaped checks -------------------------------------------
        // Each is "which dances match", so they share one projection. The predicates read against
        // the *approved* catalogue: a pending submission failing these is what review is for.

        health.Checks.Add(await DanceCheck(
            approvedDances.Where(d => !d.Videos.Any(v => v.OwnerUserId == null)),
            "dances-no-videos", "Dances with nothing to watch", "warn",
            "The page loads and offers the reader nothing. Either find it a video or delete it."));

        health.Checks.Add(await DanceCheck(
            approvedDances.Where(d => !d.DanceStyles.Any()),
            "dances-no-style", "Dances with no style", "warn",
            "A dance with no style has no /dances/{style}/{slug} URL and never appears under a style filter."));

        health.Checks.Add(await DanceCheck(
            approvedDances.Where(d => d.DanceStyles.Count > 1),
            "dances-many-styles", "Dances with more than one style", "info",
            "The 2026-06 consolidation left every dance with exactly one style. These have drifted back."));

        health.Checks.Add(await DanceCheck(
            approvedDances.Where(d => !d.DanceMusicalStyles.Any()),
            "dances-no-music", "Dances with no music tag", "info",
            "Nothing breaks, but they're missing from every music-led way into the catalogue."));

        health.Checks.Add(await DanceCheck(
            approvedDances.Where(d => d.DanceMusicalStyles.Count > 1),
            "dances-many-music", "Dances with more than one music tag", "info",
            "Same invariant as styles: one music tag each after the 2026-06 pass."));

        health.Checks.Add(await DanceCheck(
            approvedDances.Where(d => d.Description == null || d.Description == ""),
            "dances-no-description", "Dances with no description", "info",
            "The card and the detail page both fall back to bare name and tags."));

        // --- Video-shaped checks -------------------------------------------

        health.Checks.Add(await VideoCheck(
            _db.Videos.Where(v => v.OwnerUserId == null && v.VideoType == "tutorial" && !v.Segments.Any()),
            "tutorials-no-sections", "Tutorials with no Sections bar", "warn",
            "Marked as a tutorial but carrying no chips, so the one thing that makes a tutorial navigable is missing. This is the chip pipeline's queue."));

        health.Checks.Add(await VideoCheck(
            _db.Videos.Where(v => v.OwnerUserId == null && v.DurationSeconds == null),
            "videos-no-duration", "Videos with no known length", "info",
            "Runtime is blank on the card and the dance's total is short by this much. scripts/backfill_durations.py fixes these in bulk."));

        health.Checks.Add(await SharedClipCheck());
        health.Checks.Add(await DuplicateNameCheck());

        // Worst first — a page of checks nobody has ordered is a page nobody reads past.
        health.Checks = health.Checks
            .OrderByDescending(c => c.Severity == "warn")
            .ThenByDescending(c => c.Count)
            .ToList();

        return health;
    }

    private static async Task<HealthCheckDto> DanceCheck(
        IQueryable<Dance> matching, string key, string title, string severity, string detail)
    {
        var check = new HealthCheckDto
        {
            Key = key, Title = title, Severity = severity, Detail = detail,
            Count = await matching.CountAsync()
        };

        // Most-favourited first: of four hundred descriptionless dances, the ones people have
        // actually found are the ones worth an evening.
        var rows = await matching
            .OrderByDescending(d => d.FavoriteCount)
            .ThenBy(d => d.Name)
            .Take(SampleSize)
            .Select(d => new
            {
                d.Id, d.Name, d.Slug,
                StyleName = d.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault(),
                d.FavoriteCount
            })
            .ToListAsync();

        check.Items = rows.Select(r => new HealthItemDto
        {
            DanceId = r.Id,
            DanceName = r.Name,
            DanceSlug = r.Slug,
            StyleSlug = r.StyleName is null ? string.Empty : SlugGenerator.Slugify(r.StyleName),
            Note = r.FavoriteCount > 0 ? $"{r.FavoriteCount} favourite{(r.FavoriteCount == 1 ? "" : "s")}" : null
        }).ToList();

        return check;
    }

    private static async Task<HealthCheckDto> VideoCheck(
        IQueryable<Video> matching, string key, string title, string severity, string detail)
    {
        var check = new HealthCheckDto
        {
            Key = key, Title = title, Severity = severity, Detail = detail,
            Count = await matching.CountAsync()
        };

        var rows = await matching
            .OrderByDescending(v => v.ViewCount)
            .ThenBy(v => v.Id)
            .Take(SampleSize)
            .Select(v => new
            {
                v.Id, v.Title, v.DanceId,
                DanceName = v.Dance.Name,
                DanceSlug = v.Dance.Slug,
                StyleName = v.Dance.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault()
            })
            .ToListAsync();

        check.Items = rows.Select(r => new HealthItemDto
        {
            DanceId = r.DanceId,
            DanceName = r.DanceName,
            DanceSlug = r.DanceSlug,
            StyleSlug = r.StyleName is null ? string.Empty : SlugGenerator.Slugify(r.StyleName),
            VideoId = r.Id,
            VideoTitle = r.Title
        }).ToList();

        return check;
    }

    /// <summary>
    /// The mis-sourcing signature the intake rubric already grades on: one upload attached to
    /// several dances with no start time, so every one of them plays the same thing from 0:00.
    /// </summary>
    private async Task<HealthCheckDto> SharedClipCheck()
    {
        var groups = _db.Videos
            .Where(v => v.OwnerUserId == null && v.StartTime == null)
            .GroupBy(v => new { v.VideoId, v.Platform })
            .Where(g => g.Count() >= 3);

        var check = new HealthCheckDto
        {
            Key = "shared-clip-no-window",
            Title = "One upload on three or more dances, uncut",
            Severity = "warn",
            Detail = "Every one of these dances plays the same video from the start. Either give each a start/end window or move them off it.",
            Count = await groups.CountAsync()
        };

        var worst = await groups
            .OrderByDescending(g => g.Count())
            .Take(SampleSize)
            .Select(g => new { g.Key.VideoId, Uses = g.Count(), FirstId = g.Min(v => v.Id) })
            .ToListAsync();

        // A second pass for the names: the group key is the upload, and what the reader needs is
        // one dance they can open to see the problem.
        var firstIds = worst.Select(w => w.FirstId).ToList();
        var examples = await _db.Videos
            .Where(v => firstIds.Contains(v.Id))
            .Select(v => new
            {
                v.Id, v.Title, v.DanceId,
                DanceName = v.Dance.Name,
                DanceSlug = v.Dance.Slug,
                StyleName = v.Dance.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault()
            })
            .ToListAsync();

        check.Items = worst
            .Select(w => new { w.Uses, Example = examples.FirstOrDefault(e => e.Id == w.FirstId) })
            .Where(x => x.Example is not null)
            .Select(x => new HealthItemDto
            {
                DanceId = x.Example!.DanceId,
                DanceName = x.Example.DanceName,
                DanceSlug = x.Example.DanceSlug,
                StyleSlug = x.Example.StyleName is null ? string.Empty : SlugGenerator.Slugify(x.Example.StyleName),
                VideoId = x.Example.Id,
                VideoTitle = x.Example.Title,
                Note = $"on {x.Uses} dances"
            })
            .ToList();

        return check;
    }

    /// <summary>
    /// Two catalogue entries with the same name. Sometimes legitimate — the same move name in two
    /// styles is exactly what the per-style slug rule exists for — so this is grouped by name AND
    /// style, and stays "info" rather than accusing.
    /// </summary>
    private async Task<HealthCheckDto> DuplicateNameCheck()
    {
        var rows = await _db.Dances
            .Where(d => d.ReviewState == "approved")
            .Select(d => new
            {
                d.Id, d.Name, d.Slug, d.FavoriteCount,
                StyleName = d.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault()
            })
            .ToListAsync();

        // Grouped in memory: the comparison is case- and whitespace-insensitive, which Postgres
        // would do differently under its own collation, and the catalogue is under a thousand rows.
        var duplicates = rows
            .GroupBy(r => (Name: r.Name.Trim().ToLowerInvariant(), Style: r.StyleName ?? ""))
            .Where(g => g.Count() > 1)
            .OrderByDescending(g => g.Max(r => r.FavoriteCount))
            .ToList();

        return new HealthCheckDto
        {
            Key = "duplicate-dance-names",
            Title = "Two dances with the same name in one style",
            Severity = "info",
            Detail = "Usually one move that got seeded twice. Merging means moving the videos onto one and deleting the other.",
            Count = duplicates.Count,
            Items = duplicates.Take(SampleSize).SelectMany(g => g.Select(r => new HealthItemDto
            {
                DanceId = r.Id,
                DanceName = r.Name,
                DanceSlug = r.Slug,
                StyleSlug = r.StyleName is null ? string.Empty : SlugGenerator.Slugify(r.StyleName),
                Note = r.FavoriteCount > 0 ? $"{r.FavoriteCount} favourite{(r.FavoriteCount == 1 ? "" : "s")}" : null
            })).ToList()
        };
    }
}

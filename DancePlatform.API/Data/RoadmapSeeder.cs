using System.Text.Json;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Data;

/// <summary>
/// Loads the authored roadmaps in <c>Data/Roadmaps/*.json</c> into the database on boot.
///
/// Roadmaps are content, so the files are the source of truth: the seeder rebuilds a roadmap's
/// stages whenever the authored structure changes, and otherwise leaves them alone. Either way it
/// re-resolves every step's dance link on each run, so a step whose move wasn't in the catalog
/// when it was written fills in by itself once that move is added.
///
/// Unlike <see cref="SeedData"/> this is not gated on an empty database — it runs every start.
/// </summary>
public static class RoadmapSeeder
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true
    };

    public static async Task SeedAsync(AppDbContext db, string contentRoot, ILogger logger)
    {
        var dir = Path.Combine(contentRoot, "Data", "Roadmaps");
        if (!Directory.Exists(dir))
        {
            logger.LogWarning("Roadmap content directory not found at {Dir}; skipping roadmap seed.", dir);
            return;
        }

        // Small catalog (tens of rows) — load it once and match case-insensitively in memory rather
        // than pushing a LOWER()/ILIKE comparison per file into SQL.
        var styles = await db.Styles.Select(s => new { s.Id, s.Name }).ToListAsync();

        foreach (var path in Directory.EnumerateFiles(dir, "*.json").OrderBy(p => p, StringComparer.Ordinal))
        {
            RoadmapFile? file;
            try
            {
                file = JsonSerializer.Deserialize<RoadmapFile>(await File.ReadAllTextAsync(path), JsonOptions);
            }
            catch (JsonException ex)
            {
                logger.LogError(ex, "Roadmap file {File} is not valid JSON; skipping it.", Path.GetFileName(path));
                continue;
            }

            if (file is null || string.IsNullOrWhiteSpace(file.Slug) || string.IsNullOrWhiteSpace(file.StyleName))
            {
                logger.LogError("Roadmap file {File} is missing slug or styleName; skipping it.", Path.GetFileName(path));
                continue;
            }

            // Styles are catalog data — a roadmap pointing at a style that doesn't exist is an
            // authoring mistake, and inventing the style here would quietly add a bogus filter to Browse.
            var style = styles.FirstOrDefault(s => string.Equals(s.Name, file.StyleName, StringComparison.OrdinalIgnoreCase));
            if (style is null)
            {
                logger.LogError("Roadmap '{Slug}' targets unknown style '{Style}'; skipping it.", file.Slug, file.StyleName);
                continue;
            }

            await SeedOneAsync(db, file, style.Id, logger);
        }
    }

    private static async Task SeedOneAsync(AppDbContext db, RoadmapFile file, int styleId, ILogger logger)
    {

        var roadmap = await db.Roadmaps
            .Include(r => r.Stages).ThenInclude(s => s.Steps)
            .FirstOrDefaultAsync(r => r.Slug == file.Slug);

        if (roadmap is null)
        {
            roadmap = new Roadmap { Slug = file.Slug };
            db.Roadmaps.Add(roadmap);
        }

        roadmap.Title = file.Title;
        roadmap.Subtitle = file.Subtitle ?? string.Empty;
        roadmap.Description = file.Description;
        roadmap.SortOrder = file.SortOrder;
        roadmap.StyleId = styleId;

        var danceIds = await ResolveDanceIdsAsync(db, file, styleId, logger);

        if (SignatureOf(file) != SignatureOf(roadmap))
        {
            // Wholesale rebuild rather than a diff: nothing outside the file references a stage or
            // step id (progress hangs off the dance), so recreating them is safe and keeps the
            // authored order exact.
            db.RoadmapStages.RemoveRange(roadmap.Stages);
            roadmap.Stages.Clear();
            foreach (var (stage, si) in file.Stages.Select((s, i) => (s, i)))
            {
                roadmap.Stages.Add(new RoadmapStage
                {
                    Title = stage.Title,
                    Description = stage.Description,
                    SortOrder = si,
                    Steps = stage.Steps.Select((step, pi) => new RoadmapStep
                    {
                        Title = step.Title,
                        Description = step.Description,
                        SortOrder = pi,
                        DanceId = Resolve(danceIds, step.DanceSlug)
                    }).ToList()
                });
            }
        }
        else
        {
            // Structure is unchanged, so file order and stored order line up — re-point any step
            // whose dance has since appeared in (or vanished from) the catalog.
            var storedStages = roadmap.Stages.OrderBy(s => s.SortOrder).ToList();
            for (var si = 0; si < storedStages.Count; si++)
            {
                var storedSteps = storedStages[si].Steps.OrderBy(s => s.SortOrder).ToList();
                for (var pi = 0; pi < storedSteps.Count; pi++)
                {
                    storedSteps[pi].DanceId = Resolve(danceIds, file.Stages[si].Steps[pi].DanceSlug);
                }
            }
        }

        await db.SaveChangesAsync();

        if (logger.IsEnabled(LogLevel.Information))
        {
            var wanted = file.Stages.SelectMany(s => s.Steps)
                .Select(s => s.DanceSlug).Where(s => !string.IsNullOrWhiteSpace(s)).Distinct().Count();
            logger.LogInformation("Roadmap '{Slug}' seeded: {Stages} stages, {Steps} steps, {Linked}/{Wanted} moves linked.",
                file.Slug, file.Stages.Count, file.Stages.Sum(s => s.Steps.Count), danceIds.Count, wanted);
        }
    }

    private static int? Resolve(Dictionary<string, int> danceIds, string? slug) =>
        !string.IsNullOrWhiteSpace(slug) && danceIds.TryGetValue(slug, out var id) ? id : null;

    /// <summary>
    /// Maps each authored dance slug to a dance id. Dance slugs are unique per style, not globally
    /// (see AppDbContext), so the lookup is scoped to the roadmap's style — otherwise "the-heel-toe"
    /// in Waacking could resolve to a same-named hip-hop step.
    /// </summary>
    private static async Task<Dictionary<string, int>> ResolveDanceIdsAsync(
        AppDbContext db, RoadmapFile file, int styleId, ILogger logger)
    {
        var slugs = file.Stages
            .SelectMany(s => s.Steps)
            .Select(s => s.DanceSlug)
            .Where(s => !string.IsNullOrWhiteSpace(s))
            .Select(s => s!)
            .Distinct()
            .ToList();

        if (slugs.Count == 0) return new Dictionary<string, int>();

        var found = await db.Dances
            .Where(d => slugs.Contains(d.Slug) && d.DanceStyles.Any(ds => ds.StyleId == styleId))
            .Select(d => new { d.Slug, d.Id })
            .ToDictionaryAsync(d => d.Slug, d => d.Id);

        foreach (var missing in slugs.Where(s => !found.ContainsKey(s)))
        {
            // Not fatal: the step still renders from its authored title as a "no video yet" node.
            logger.LogWarning("Roadmap '{Slug}': no {Style} dance with slug '{Dance}' — step will show as unlinked.",
                file.Slug, file.StyleName, missing);
        }

        return found;
    }

    // Fingerprints the authored structure and copy, so an unchanged file is a no-op instead of a
    // delete-and-reinsert on every boot. Serialised rather than string-joined so no separator can
    // collide with the prose. Dance links are deliberately excluded: the DB stores the resolved id,
    // not the authored slug, so the two sides can't be compared — and they don't need to be, since
    // every run re-resolves them from the file either way.
    private static string SignatureOf(RoadmapFile file) =>
        JsonSerializer.Serialize(file.Stages.Select(s => new
        {
            s.Title,
            s.Description,
            Steps = s.Steps.Select(p => new { p.Title, p.Description })
        }));

    private static string SignatureOf(Roadmap roadmap) =>
        JsonSerializer.Serialize(roadmap.Stages.OrderBy(s => s.SortOrder).Select(s => new
        {
            s.Title,
            s.Description,
            Steps = s.Steps.OrderBy(p => p.SortOrder).Select(p => new { p.Title, p.Description })
        }));

    private sealed class RoadmapFile
    {
        public string Slug { get; set; } = string.Empty;
        public string StyleName { get; set; } = string.Empty;
        public string Title { get; set; } = string.Empty;
        public string? Subtitle { get; set; }
        public string? Description { get; set; }
        public int SortOrder { get; set; }
        public List<StageFile> Stages { get; set; } = new();
    }

    private sealed class StageFile
    {
        public string Title { get; set; } = string.Empty;
        public string? Description { get; set; }
        public List<StepFile> Steps { get; set; } = new();
    }

    private sealed class StepFile
    {
        public string Title { get; set; } = string.Empty;
        public string? Description { get; set; }
        public string? DanceSlug { get; set; }
    }
}

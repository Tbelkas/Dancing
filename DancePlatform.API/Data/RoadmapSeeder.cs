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
        var segmentIds = await ResolveSegmentIdsAsync(db, file, danceIds, logger);

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
                        Key = StepKey(step),
                        Title = step.Title,
                        Description = step.Description,
                        SortOrder = pi,
                        DanceId = Resolve(danceIds, step.DanceSlug),
                        VideoSegmentId = Resolve(segmentIds, SegmentKey(step))
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
                    var authored = file.Stages[si].Steps[pi];
                    storedSteps[pi].DanceId = Resolve(danceIds, authored.DanceSlug);
                    storedSteps[pi].VideoSegmentId = Resolve(segmentIds, SegmentKey(authored));
                }
            }
        }

        await db.SaveChangesAsync();

        // Edges last: they need the step rows to exist so keys can be turned into ids.
        var edges = await SyncPrerequisitesAsync(db, file, roadmap, logger);

        if (logger.IsEnabled(LogLevel.Information))
        {
            var wanted = file.Stages.SelectMany(s => s.Steps)
                .Select(s => s.DanceSlug).Where(s => !string.IsNullOrWhiteSpace(s)).Distinct().Count();
            logger.LogInformation(
                "Roadmap '{Slug}' seeded: {Stages} stages, {Steps} steps, {Linked}/{Wanted} moves linked, {Segments} pinned to a clip, {Edges} tree edges.",
                file.Slug, file.Stages.Count, file.Stages.Sum(s => s.Steps.Count), danceIds.Count, wanted,
                segmentIds.Count, edges);
        }
    }

    /// <summary>
    /// Rebuilds the roadmap's prerequisite edges from the authored `requires` keys. Always a full
    /// replace: edges are cheap, and a diff would have to reason about steps that were just
    /// recreated. Unknown keys and cycles are dropped with a logged error rather than throwing —
    /// a bad edge should cost one connector, not the whole path (and never boot).
    /// </summary>
    private static async Task<int> SyncPrerequisitesAsync(
        AppDbContext db, RoadmapFile file, Roadmap roadmap, ILogger logger)
    {
        var stepsByKey = roadmap.Stages
            .SelectMany(s => s.Steps)
            .GroupBy(s => s.Key)
            .ToDictionary(g => g.Key, g => g.First().Id, StringComparer.OrdinalIgnoreCase);

        var existing = await db.RoadmapStepPrerequisites
            .Where(p => stepsByKey.Values.Contains(p.StepId))
            .ToListAsync();
        db.RoadmapStepPrerequisites.RemoveRange(existing);

        // Authored adjacency, keyed the same way the steps are, for the cycle check below.
        var authored = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
        foreach (var step in file.Stages.SelectMany(s => s.Steps))
        {
            var key = StepKey(step);
            var deps = new List<string>();
            foreach (var required in step.Requires.Where(r => !string.IsNullOrWhiteSpace(r)))
            {
                if (!stepsByKey.ContainsKey(required))
                {
                    logger.LogError("Roadmap '{Slug}': step '{Step}' requires unknown key '{Key}'; edge dropped.",
                        file.Slug, key, required);
                    continue;
                }
                if (string.Equals(required, key, StringComparison.OrdinalIgnoreCase))
                {
                    logger.LogError("Roadmap '{Slug}': step '{Step}' requires itself; edge dropped.", file.Slug, key);
                    continue;
                }
                deps.Add(required);
            }
            authored[key] = deps;
        }

        var added = 0;
        foreach (var (key, deps) in authored)
        {
            foreach (var required in deps)
            {
                // A cycle would make every node in it unreachable and hang any depth walk.
                if (CreatesCycle(authored, from: required, to: key))
                {
                    logger.LogError("Roadmap '{Slug}': '{Step}' requires '{Key}' but that closes a cycle; edge dropped.",
                        file.Slug, key, required);
                    continue;
                }
                db.RoadmapStepPrerequisites.Add(new RoadmapStepPrerequisite
                {
                    StepId = stepsByKey[key],
                    PrerequisiteStepId = stepsByKey[required]
                });
                added++;
            }
        }

        await db.SaveChangesAsync();
        return added;
    }

    /// <summary>True when <paramref name="to"/> is already reachable from <paramref name="from"/>.</summary>
    private static bool CreatesCycle(Dictionary<string, List<string>> authored, string from, string to)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var stack = new Stack<string>([from]);
        while (stack.Count > 0)
        {
            var current = stack.Pop();
            if (string.Equals(current, to, StringComparison.OrdinalIgnoreCase)) return true;
            if (!seen.Add(current)) continue;
            if (authored.TryGetValue(current, out var deps))
                foreach (var d in deps) stack.Push(d);
        }
        return false;
    }

    private static string StepKey(StepFile step) =>
        string.IsNullOrWhiteSpace(step.Key) ? Services.SlugGenerator.Slugify(step.Title) : step.Key.Trim();

    private static int? Resolve(Dictionary<string, int> ids, string? key) =>
        !string.IsNullOrWhiteSpace(key) && ids.TryGetValue(key, out var id) ? id : null;

    /// <summary>A segment is only meaningful inside its dance, so it's keyed by both.</summary>
    private static string? SegmentKey(StepFile step) =>
        string.IsNullOrWhiteSpace(step.DanceSlug) || string.IsNullOrWhiteSpace(step.SegmentLabel)
            ? null
            : $"{step.DanceSlug}{step.SegmentLabel}";

    /// <summary>
    /// Maps each authored (danceSlug, segmentLabel) pair to a VideoSegment id, looked up among
    /// the global videos of that dance. Personal videos are excluded — roadmap content must be
    /// the same for every viewer.
    /// </summary>
    private static async Task<Dictionary<string, int>> ResolveSegmentIdsAsync(
        AppDbContext db, RoadmapFile file, Dictionary<string, int> danceIds, ILogger logger)
    {
        var wanted = file.Stages
            .SelectMany(s => s.Steps)
            .Select(s => (Step: s, Key: SegmentKey(s)))
            .Where(x => x.Key is not null)
            .GroupBy(x => x.Key!)
            .Select(g => (Key: g.Key, g.First().Step.DanceSlug, g.First().Step.SegmentLabel))
            .ToList();

        var found = new Dictionary<string, int>();
        if (wanted.Count == 0) return found;

        var danceIdList = wanted.Select(w => Resolve(danceIds, w.DanceSlug)).OfType<int>().Distinct().ToList();
        var candidates = await db.VideoSegments
            .Where(seg => seg.Video.OwnerUserId == null && danceIdList.Contains(seg.Video.DanceId))
            .Select(seg => new { seg.Id, seg.Label, seg.StartTime, seg.Video.DanceId, VideoAdded = seg.Video.DateAdded })
            .ToListAsync();

        foreach (var (key, danceSlug, label) in wanted)
        {
            if (Resolve(danceIds, danceSlug) is not int danceId)
            {
                logger.LogWarning("Roadmap '{Slug}': step wants segment '{Label}' but its dance '{Dance}' did not resolve.",
                    file.Slug, label, danceSlug);
                continue;
            }

            var matches = candidates
                .Where(c => c.DanceId == danceId && string.Equals(c.Label, label, StringComparison.OrdinalIgnoreCase))
                .OrderBy(c => c.VideoAdded).ThenBy(c => c.StartTime)
                .ToList();

            if (matches.Count == 0)
            {
                // Not fatal: the step falls back to covering the whole dance.
                logger.LogWarning("Roadmap '{Slug}': dance '{Dance}' has no segment labelled '{Label}' — step widens to the whole move.",
                    file.Slug, danceSlug, label);
                continue;
            }

            if (matches.Count > 1)
            {
                // Generic labels ("Intro") repeat across a dance's videos. Deterministic, but
                // almost certainly not what the author meant — say so.
                logger.LogWarning("Roadmap '{Slug}': label '{Label}' matches {Count} segments on '{Dance}'; taking the earliest.",
                    file.Slug, label, matches.Count, danceSlug);
            }

            found[key] = matches[0].Id;
        }

        return found;
    }

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
            Steps = s.Steps.Select(p => new { Key = StepKey(p), p.Title, p.Description })
        }));

    private static string SignatureOf(Roadmap roadmap) =>
        JsonSerializer.Serialize(roadmap.Stages.OrderBy(s => s.SortOrder).Select(s => new
        {
            s.Title,
            s.Description,
            Steps = s.Steps.OrderBy(p => p.SortOrder).Select(p => new { p.Key, p.Title, p.Description })
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
        /// <summary>Stable id used by other steps' <see cref="Requires"/>. Defaults to a slug of the title.</summary>
        public string? Key { get; set; }

        public string Title { get; set; } = string.Empty;
        public string? Description { get; set; }
        public string? DanceSlug { get; set; }

        /// <summary>Optional: narrows the step to one section of one of the dance's videos.</summary>
        public string? SegmentLabel { get; set; }

        /// <summary>Keys of steps that come before this one. Empty = a root of the tree.</summary>
        public List<string> Requires { get; set; } = new();
    }
}

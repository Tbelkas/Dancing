using System.Text.Json;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Data;

/// <summary>
/// Loads the authored glossaries in <c>Data/Glossary/*.json</c> into the database on every boot.
///
/// Terms are upserted by (style, slug) rather than rebuilt, because users' learned marks hang off
/// the term rows — rewording a description must never cost anyone their progress. A term dropped
/// from its file is deleted (and its marks with it), so renaming a slug is the one edit that does
/// cost progress: keep slugs stable.
///
/// Dance links re-resolve each run, same as roadmap steps, so a term authored before its move
/// reached the catalog picks up the video by itself later.
/// </summary>
public static class GlossarySeeder
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true
    };

    public static async Task SeedAsync(AppDbContext db, string contentRoot, ILogger logger)
    {
        var dir = Path.Combine(contentRoot, "Data", "Glossary");
        if (!Directory.Exists(dir))
        {
            logger.LogWarning("Glossary content directory not found at {Dir}; skipping glossary seed.", dir);
            return;
        }

        var styles = await db.Styles.Select(s => new { s.Id, s.Name }).ToListAsync();

        foreach (var path in Directory.EnumerateFiles(dir, "*.json").OrderBy(p => p, StringComparer.Ordinal))
        {
            GlossaryFile? file;
            try
            {
                file = JsonSerializer.Deserialize<GlossaryFile>(await File.ReadAllTextAsync(path), JsonOptions);
            }
            catch (JsonException ex)
            {
                logger.LogError(ex, "Glossary file {File} is not valid JSON; skipping it.", Path.GetFileName(path));
                continue;
            }

            if (file is null || string.IsNullOrWhiteSpace(file.StyleName))
            {
                logger.LogError("Glossary file {File} has no styleName; skipping it.", Path.GetFileName(path));
                continue;
            }

            var style = styles.FirstOrDefault(s => string.Equals(s.Name, file.StyleName, StringComparison.OrdinalIgnoreCase));
            if (style is null)
            {
                logger.LogError("Glossary {File} targets unknown style '{Style}'; skipping it.", Path.GetFileName(path), file.StyleName);
                continue;
            }

            await SeedOneAsync(db, file, style.Id, Path.GetFileName(path), logger);
        }
    }

    private static async Task SeedOneAsync(AppDbContext db, GlossaryFile file, int styleId, string fileName, ILogger logger)
    {
        var authored = file.Categories
            .SelectMany(c => c.Terms.Select(t => (Category: c.Name, Term: t)))
            .ToList();

        // A duplicate slug would make the upsert write the second over the first — refuse the
        // file rather than silently losing a term.
        var dupes = authored.GroupBy(a => a.Term.Slug, StringComparer.OrdinalIgnoreCase).Where(g => g.Count() > 1).Select(g => g.Key).ToList();
        if (dupes.Count > 0 || authored.Any(a => string.IsNullOrWhiteSpace(a.Term.Slug) || string.IsNullOrWhiteSpace(a.Term.Name)))
        {
            logger.LogError("Glossary {File} has blank or duplicate slugs ({Dupes}); skipping it.", fileName, string.Join(", ", dupes));
            return;
        }

        var danceSlugs = authored.Select(a => a.Term.DanceSlug).Where(s => !string.IsNullOrWhiteSpace(s)).Distinct().ToList();
        var dances = await db.Dances
            .Where(d => danceSlugs.Contains(d.Slug) && d.ReviewState == "approved")
            .Select(d => new { d.Id, d.Slug })
            .ToDictionaryAsync(d => d.Slug, d => d.Id);

        var existing = await db.GlossaryTerms.Where(t => t.StyleId == styleId).ToListAsync();
        var bySlug = existing.ToDictionary(t => t.Slug, StringComparer.OrdinalIgnoreCase);

        var order = 0;
        foreach (var (category, a) in authored)
        {
            if (!bySlug.TryGetValue(a.Slug, out var row))
            {
                row = new GlossaryTerm { StyleId = styleId, Slug = a.Slug.ToLowerInvariant() };
                db.GlossaryTerms.Add(row);
            }

            int? danceId = null;
            if (!string.IsNullOrWhiteSpace(a.DanceSlug))
            {
                if (dances.TryGetValue(a.DanceSlug, out var id)) danceId = id;
                else logger.LogWarning("Glossary {File}: term '{Term}' names unknown dance '{Dance}'; left unlinked.", fileName, a.Slug, a.DanceSlug);
            }

            if (!Enum.TryParse<DifficultyLevel>(a.Difficulty, ignoreCase: true, out var difficulty))
                difficulty = DifficultyLevel.None;

            row.Name = a.Name;
            row.Category = category;
            row.Aliases = a.Aliases;
            row.Summary = a.Summary;
            row.Description = a.Description;
            row.Steps = a.Steps;
            row.Tips = a.Tips;
            row.Related = a.Related;
            row.Difficulty = difficulty;
            row.IsLearnable = a.Learnable;
            row.DanceId = danceId;
            row.SortOrder = order++;
        }

        var authoredSlugs = authored.Select(a => a.Term.Slug).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var removed = existing.Where(t => !authoredSlugs.Contains(t.Slug)).ToList();
        if (removed.Count > 0)
        {
            logger.LogWarning("Glossary {File}: removing {Count} term(s) no longer authored: {Slugs}.",
                fileName, removed.Count, string.Join(", ", removed.Select(t => t.Slug)));
            db.GlossaryTerms.RemoveRange(removed);
        }

        await db.SaveChangesAsync();
    }

    private sealed class GlossaryFile
    {
        public string StyleName { get; set; } = string.Empty;
        public List<GlossaryCategoryFile> Categories { get; set; } = new();
    }

    private sealed class GlossaryCategoryFile
    {
        public string Name { get; set; } = string.Empty;
        public List<GlossaryTermFile> Terms { get; set; } = new();
    }

    private sealed class GlossaryTermFile
    {
        public string Slug { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public List<string> Aliases { get; set; } = new();
        public string Summary { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public List<string> Steps { get; set; } = new();
        public List<string> Tips { get; set; } = new();
        public List<string> Related { get; set; } = new();
        public string? Difficulty { get; set; }
        public bool Learnable { get; set; } = true;
        public string? DanceSlug { get; set; }
    }
}

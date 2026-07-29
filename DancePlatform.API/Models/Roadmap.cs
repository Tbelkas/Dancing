namespace DancePlatform.API.Models;

/// <summary>
/// A curated learning path through one style: an ordered list of stages, each holding the
/// moves to learn at that point. Roadmaps are content, not user data — they are authored in
/// <c>Data/Roadmaps/*.json</c> and upserted on boot by <see cref="Data.RoadmapSeeder"/>.
/// Progress is not stored here; it is read from the existing learned/in-progress joins.
/// </summary>
public class Roadmap
{
    public int Id { get; set; }

    /// <summary>URL key, unique. Usually the style slug ("house", "waacking").</summary>
    public string Slug { get; set; } = string.Empty;

    public string Title { get; set; } = string.Empty;

    /// <summary>One-line pitch shown under the title and on the index card.</summary>
    public string Subtitle { get; set; } = string.Empty;

    /// <summary>Longer intro paragraph shown at the top of the path.</summary>
    public string? Description { get; set; }

    public int StyleId { get; set; }
    public Style Style { get; set; } = null!;

    /// <summary>Position on the roadmap index; ties break on Title.</summary>
    public int SortOrder { get; set; }

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public List<RoadmapStage> Stages { get; set; } = new();
}

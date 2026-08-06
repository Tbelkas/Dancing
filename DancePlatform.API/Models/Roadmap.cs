namespace DancePlatform.API.Models;

/// <summary>
/// A learning path through one style: an ordered list of stages, each holding the moves to learn
/// at that point. Progress is not stored here; it is read from the existing learned/in-progress
/// joins.
///
/// Two kinds share this table, told apart by <see cref="OwnerUserId"/>:
/// <list type="bullet">
/// <item><b>Curated</b> (owner null) — content, authored in <c>Data/Roadmaps/*.json</c> and
/// upserted on boot by <see cref="Data.RoadmapSeeder"/>. Visible to everyone.</item>
/// <item><b>Personal</b> (owner set) — a skill tree a user built for themselves through the
/// builder. User data: only the owner can read or edit it, and the seeder never touches it.</item>
/// </list>
/// </summary>
public class Roadmap
{
    public int Id { get; set; }

    /// <summary>URL key, unique across both kinds. Usually the style slug ("house", "waacking").</summary>
    public string Slug { get; set; } = string.Empty;

    public string Title { get; set; } = string.Empty;

    /// <summary>One-line pitch shown under the title and on the index card.</summary>
    public string Subtitle { get; set; } = string.Empty;

    /// <summary>Longer intro paragraph shown at the top of the path.</summary>
    public string? Description { get; set; }

    public int StyleId { get; set; }
    public Style Style { get; set; } = null!;

    /// <summary>
    /// Null for the curated paths. Set to the author when a user builds their own tree — which
    /// makes the row private to them, and makes it invisible to <see cref="Data.RoadmapSeeder"/>
    /// (a personal tree is not authored content and must never be rebuilt from a file).
    /// </summary>
    public int? OwnerUserId { get; set; }
    public User? Owner { get; set; }

    /// <summary>Position on the roadmap index; ties break on Title.</summary>
    public int SortOrder { get; set; }

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    /// <summary>Last edit through the builder. Null for curated paths, which are seeded not edited.</summary>
    public DateTime? DateModified { get; set; }

    public List<RoadmapStage> Stages { get; set; } = new();
}

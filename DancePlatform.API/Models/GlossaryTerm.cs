namespace DancePlatform.API.Models;

/// <summary>
/// One entry in a style's glossary: a named move (or, when <see cref="IsLearnable"/> is false, a
/// concept such as "on the one") described in depth.
///
/// Glossaries are authored content, like roadmaps: <c>Data/Glossary/&lt;style&gt;.json</c> is the
/// source of truth and <see cref="Data.GlossarySeeder"/> upserts it on every boot, keyed on
/// (<see cref="StyleId"/>, <see cref="Slug"/>). The catalog is deliberately NOT the source — a
/// style's dances are whatever tutorials were found, with seeded names and descriptions that are
/// not reliable enough to be the reference text. A term only borrows a dance for its video.
/// </summary>
public class GlossaryTerm
{
    public int Id { get; set; }

    public int StyleId { get; set; }
    public Style Style { get; set; } = null!;

    /// <summary>Stable across edits — learned marks hang off the row, and the row is found by this.</summary>
    public string Slug { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;

    /// <summary>Other names the move goes by in classes and battles.</summary>
    public List<string> Aliases { get; set; } = new();

    /// <summary>The authored section it sits in (Grooves, Footwork, Lofting…). Order comes from <see cref="SortOrder"/>.</summary>
    public string Category { get; set; } = string.Empty;

    /// <summary>One line, shown collapsed.</summary>
    public string Summary { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;

    /// <summary>How to do it, one instruction per entry. Empty for concepts.</summary>
    public List<string> Steps { get; set; } = new();

    /// <summary>Cues and common mistakes.</summary>
    public List<string> Tips { get; set; } = new();

    /// <summary>Slugs of related terms in the same glossary. Unknown slugs are dropped when served.</summary>
    public List<string> Related { get; set; } = new();

    public DifficultyLevel Difficulty { get; set; } = DifficultyLevel.None;

    /// <summary>False for concepts — there is nothing to tick off on "the one".</summary>
    public bool IsLearnable { get; set; } = true;

    /// <summary>
    /// The catalog dance whose videos demonstrate this move, resolved from the authored slug on
    /// every boot. Null when the catalog has nothing trustworthy for it yet.
    /// </summary>
    public int? DanceId { get; set; }
    public Dance? Dance { get; set; }

    public int SortOrder { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public ICollection<UserLearnedGlossaryTerm> LearnedBy { get; set; } = new List<UserLearnedGlossaryTerm>();
}

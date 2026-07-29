namespace DancePlatform.API.Models;

/// <summary>
/// One move to learn within a <see cref="RoadmapStage"/>.
///
/// The step's own <see cref="Title"/> is authoritative: a path teaches the moves a style
/// actually needs, whether or not the catalog covers them yet. <see cref="DanceId"/> is the
/// optional link to a catalog move — when it is set the UI shows that dance's videos and the
/// user's learned/in-progress status; when it is null the step renders as "no video yet".
/// The seeder re-resolves the link on every boot, so a step fills in by itself once a
/// matching dance is added.
/// </summary>
public class RoadmapStep
{
    public int Id { get; set; }

    public int RoadmapStageId { get; set; }
    public RoadmapStage Stage { get; set; } = null!;

    public string Title { get; set; } = string.Empty;

    /// <summary>What to work on, in the authored voice — not the dance's own description.</summary>
    public string? Description { get; set; }

    public int SortOrder { get; set; }

    public int? DanceId { get; set; }
    public Dance? Dance { get; set; }

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;
}

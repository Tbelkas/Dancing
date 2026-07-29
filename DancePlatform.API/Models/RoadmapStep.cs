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

    /// <summary>
    /// Stable author-chosen id, unique within its roadmap ("jack", "toe-twist"). Prerequisites
    /// are authored against these, so reordering or renaming a step's title doesn't break the
    /// graph. Falls back to a slug of the title when the JSON omits it.
    /// </summary>
    public string Key { get; set; } = string.Empty;

    public string Title { get; set; } = string.Empty;

    /// <summary>What to work on, in the authored voice — not the dance's own description.</summary>
    public string? Description { get; set; }

    public int SortOrder { get; set; }

    public int? DanceId { get; set; }
    public Dance? Dance { get; set; }

    /// <summary>
    /// Optional narrowing of <see cref="DanceId"/> to one section of one of its videos.
    ///
    /// Multi-move tutorials are deliberately kept whole and attached to a single canonical
    /// dance (see VIDEO_FIXUP.md) with their sub-moves recorded as segments. Without this a
    /// step could only say "watch the 12-minute waacking tutorial"; with it, the step lands on
    /// the 4 minutes that teach the arm roll. Null = the step covers the whole dance.
    /// </summary>
    public int? VideoSegmentId { get; set; }
    public VideoSegment? VideoSegment { get; set; }

    /// <summary>
    /// Steps that should be learned before this one. Progression through a style is a graph,
    /// not a line — the twists and the travelling steps both come off the jack but don't depend
    /// on each other — so the path renders as a tree rather than a numbered list.
    /// </summary>
    public List<RoadmapStepPrerequisite> Prerequisites { get; set; } = new();

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;
}

namespace DancePlatform.API.DTOs.Roadmap;

/// <summary>
/// The whole of a personal skill tree, as the builder holds it. Create and update both take this
/// shape and the service replaces the stored stages/steps/edges wholesale — the same approach
/// <see cref="Data.RoadmapSeeder"/> takes with the authored files, and for the same reason:
/// nothing outside the roadmap references a stage or step id (progress hangs off the dance), so
/// recreating them is safe and keeps the authored order exact without a diff to reason about.
/// </summary>
public class SaveRoadmapRequest
{
    public string Title { get; set; } = string.Empty;

    /// <summary>One-line pitch. Optional — the builder fills a default when it's blank.</summary>
    public string? Subtitle { get; set; }

    public string? Description { get; set; }

    /// <summary>The style the tree is for. Required: it scopes the move picker and the catalog links.</summary>
    public int StyleId { get; set; }

    public List<SaveRoadmapStageRequest> Stages { get; set; } = new();
}

public class SaveRoadmapStageRequest
{
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public List<SaveRoadmapStepRequest> Steps { get; set; } = new();
}

public class SaveRoadmapStepRequest
{
    /// <summary>
    /// The step's id within this request — what <see cref="Requires"/> names. The client owns
    /// these; the server sanitises and de-duplicates them, then rewrites the edges through the
    /// same mapping, so a client that reuses a key gets a working tree rather than a 400.
    /// Blank falls back to a slug of the title.
    /// </summary>
    public string? Key { get; set; }

    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }

    /// <summary>Optional link to a catalog move. Unlike the authored files this is an id, not a
    /// slug — the builder picks from search results, so it already has one.</summary>
    public int? DanceId { get; set; }

    /// <summary>Optional narrowing to one section of one of that dance's videos.</summary>
    public int? VideoSegmentId { get; set; }

    /// <summary>
    /// Optional link to one of the caller's own roadmaps, making this step a module gateway
    /// instead of a move. Ignored when <see cref="DanceId"/> is also set — a step is one or the
    /// other — and dropped rather than rejected when it names a tree the caller doesn't own, is
    /// already claimed by another step, or would close a loop.
    ///
    /// Unlinking here does <b>not</b> delete the child: it becomes a normal top-level tree the
    /// user still owns and can see on their index. Losing a subtree to a mis-click would be far
    /// worse than an extra row on the shelf.
    /// </summary>
    public int? ChildRoadmapId { get; set; }

    /// <summary>Keys of the steps that come before this one. Empty = a root of the tree.</summary>
    public List<string> Requires { get; set; } = new();
}

/// <summary>
/// The body of <c>PUT /roadmaps/{id}/share</c>. Its own request rather than a field on
/// <see cref="SaveRoadmapRequest"/>, so a builder tab opened before the toggle can't unshare a
/// tree by saving stale structure over it.
/// </summary>
public class SetRoadmapSharedRequest
{
    public bool Shared { get; set; }
}

/// <summary>
/// A save's outcome. The builder can put a bad tree together in ways the seeder's files can't
/// (a cycle drawn by hand, a style that was deleted), and silently dropping the edge the user
/// just added would look like the save failed at random — so a save either lands whole or comes
/// back with a message the builder can show against the offending step.
/// </summary>
public record RoadmapSaveResult(RoadmapDto? Roadmap, string? Error)
{
    public static RoadmapSaveResult Ok(RoadmapDto roadmap) => new(roadmap, null);
    public static RoadmapSaveResult Fail(string error) => new(null, error);

    /// <summary>
    /// No roadmap and nothing wrong with the request: the id isn't one of the caller's own trees.
    /// A curated path and someone else's tree are the same answer — both 404, so the endpoint
    /// never confirms that a private tree exists.
    /// </summary>
    public static RoadmapSaveResult NotFound => new(null, null);
}

using DancePlatform.API.DTOs.Roadmap;

namespace DancePlatform.API.Services;

public interface IRoadmapService
{
    /// <summary>
    /// The curated paths plus the caller's own skill trees, with their progress counts.
    /// Someone else's personal tree is never included — they are private to their owner.
    /// </summary>
    Task<List<RoadmapSummaryDto>> GetAllAsync(int? userId);

    /// <summary>
    /// The full path by slug (or numeric id), or null when it doesn't exist — or belongs to
    /// another user, which is deliberately indistinguishable from not existing.
    /// </summary>
    Task<RoadmapDto?> GetByIdOrSlugAsync(string idOrSlug, int? userId);

    /// <summary>Builds a new personal skill tree owned by <paramref name="userId"/>.</summary>
    Task<RoadmapSaveResult> CreateAsync(int userId, SaveRoadmapRequest request);

    /// <summary>
    /// Replaces a personal tree's metadata, stages, steps and edges. Returns a null roadmap with
    /// no error when the id isn't one of the caller's own trees — curated paths are read-only
    /// here, they are edited by changing their JSON file.
    /// </summary>
    Task<RoadmapSaveResult> UpdateAsync(int userId, int id, SaveRoadmapRequest request);

    /// <summary>Deletes one of the caller's own trees. False when it isn't theirs.</summary>
    Task<bool> DeleteAsync(int userId, int id);

    /// <summary>
    /// Shares one of the caller's own trees, or stops sharing it. Null when it isn't theirs.
    ///
    /// Kept off <see cref="SaveRoadmapRequest"/> on purpose: a save replaces the whole tree, so
    /// carrying the flag there would let a builder tab opened before the toggle silently unshare
    /// it again.
    /// </summary>
    Task<RoadmapDto?> SetSharedAsync(int userId, int id, bool shared);

    /// <summary>
    /// Copies any roadmap the caller can see into a personal tree of their own, so a curated
    /// path can be the starting point for a personalised one rather than a blank page.
    /// </summary>
    Task<RoadmapSaveResult> CopyAsync(int userId, string idOrSlug);
}

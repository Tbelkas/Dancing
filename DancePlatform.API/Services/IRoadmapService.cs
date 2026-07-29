using DancePlatform.API.DTOs.Roadmap;

namespace DancePlatform.API.Services;

public interface IRoadmapService
{
    /// <summary>Every roadmap, in authored order, with the caller's progress counts.</summary>
    Task<List<RoadmapSummaryDto>> GetAllAsync(int? userId);

    /// <summary>The full path by slug (or numeric id), or null when it doesn't exist.</summary>
    Task<RoadmapDto?> GetByIdOrSlugAsync(string idOrSlug, int? userId);
}

using DancePlatform.API.DTOs.Dance;

namespace DancePlatform.API.Services;

public enum CreateDanceResult
{
    Ok,
    /// <summary>A dance of that name already exists in one of the requested styles; the returned
    /// DTO is the existing one, so the caller can point at it instead of making a second.</summary>
    DuplicateName
}

public interface IDanceService
{
    // isAdmin threads through the reads because dances awaiting review are visible to their
    // creator and to admins, and to nobody else. It is a parameter rather than a global query
    // filter so that the creator's own dance keeps working everywhere it already appears.
    Task<List<DanceNameDto>> GetNamesAsync(int? userId = null, bool isAdmin = false);
    Task<DanceDto?> GetByIdAsync(int id, int? userId, bool isAdmin = false);
    Task<DanceDto?> GetBySlugAsync(string slug, int? userId, bool isAdmin = false);
    Task<DanceDto?> GetByStyleAndSlugAsync(string styleSlug, string danceSlug, int? userId, bool isAdmin = false);
    Task<int> ReslugAllAsync();
    Task<List<DanceDto>> GetRecommendedAsync(int id, int? userId, int limit = 8);

    /// <summary>The alphabetical prev/next dances within the given dance's canonical style (see <see cref="DanceNeighborsDto"/>).</summary>
    Task<DanceNeighborsDto> GetNeighborsAsync(int id, int? userId);
    Task<(CreateDanceResult Result, DanceDto? Dance)> CreateAsync(CreateDanceRequest request, int? ownerUserId, bool isAdmin);
    Task<DanceDto?> UpdateAsync(int id, UpdateDanceRequest request);

    /// <summary>The queue an admin reviews: user-added dances nobody has looked at yet.</summary>
    Task<List<DanceDto>> GetPendingAsync(int limit = 100);

    /// <summary>Approves ("approved") or re-holds ("pending") a dance.</summary>
    Task<DanceDto?> SetReviewStateAsync(int id, string reviewState);

    /// <summary>Admins may delete anything; a contributor may withdraw only their own dance,
    /// and only while it is still pending.</summary>
    Task<bool> DeleteAsync(int id, int? requesterId, bool isAdmin);
    Task<bool> ToggleFavoriteAsync(int userId, int danceId);
    Task<DanceStatusDto> SetStatusAsync(int userId, int danceId, string status);
    Task<SearchDancesResult> SearchAsync(string query, int? styleId, int? musicalStyleId, string? difficulty, string? status, string? sortBy, int? userId, int page = 1, int pageSize = 24, bool favoritesOnly = false);

    /// <summary>One random dance matching the same filters as <see cref="SearchAsync"/>, or null if none match.</summary>
    Task<DanceDto?> RandomAsync(string query, int? styleId, int? musicalStyleId, string? difficulty, string? status, int? userId, bool favoritesOnly = false);
}

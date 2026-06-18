using DancePlatform.API.DTOs.Dance;

namespace DancePlatform.API.Services;

public interface IDanceService
{
    Task<List<DanceNameDto>> GetNamesAsync();
    Task<DanceDto?> GetByIdAsync(int id, int? userId);
    Task<DanceDto?> GetBySlugAsync(string slug, int? userId);
    Task<List<DanceDto>> GetRecommendedAsync(int id, int? userId, int limit = 8);
    Task<DanceDto> CreateAsync(CreateDanceRequest request);
    Task<DanceDto?> UpdateAsync(int id, UpdateDanceRequest request);
    Task<bool> DeleteAsync(int id);
    Task<bool> ToggleFavoriteAsync(int userId, int danceId);
    Task<bool> ToggleLearnedAsync(int userId, int danceId);
    Task<bool> ToggleInProgressAsync(int userId, int danceId);
    Task<DanceStatusDto> SetStatusAsync(int userId, int danceId, string status);
    Task<SearchDancesResult> SearchAsync(string query, int? styleId, int? musicalStyleId, string? difficulty, string? status, string? sortBy, int? userId, int page = 1, int pageSize = 24);
    Task<DanceDto?> RateDanceAsync(int userId, int danceId, int rating);
}

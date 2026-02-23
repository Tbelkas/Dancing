using DancePlatform.API.DTOs.Dance;

namespace DancePlatform.API.Services;

public interface IDanceService
{
    Task<List<DanceDto>> GetAllAsync(int? userId);
    Task<DanceDto?> GetByIdAsync(int id, int? userId);
    Task<DanceDto> CreateAsync(CreateDanceRequest request);
    Task<DanceDto?> UpdateAsync(int id, UpdateDanceRequest request);
    Task<bool> DeleteAsync(int id);
    Task<bool> ToggleFavoriteAsync(int userId, int danceId);
    Task<bool> ToggleLearnedAsync(int userId, int danceId);
    Task<List<DanceDto>> SearchAsync(string query, int? styleId, int? userId);
}

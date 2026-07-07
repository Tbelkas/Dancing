using DancePlatform.API.DTOs.Choreo;
using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

public interface IChoreoService
{
    Task<List<ChoreoDto>> GetMineAsync(int userId);
    Task<ChoreoDto?> GetByIdAsync(int userId, int choreoId);
    Task<ChoreoDto?> CreateAsync(int userId, CreateChoreoRequest request);
    Task<ChoreoDto?> UpdateAsync(int userId, int choreoId, UpdateChoreoRequest request);
    Task<bool> DeleteAsync(int userId, int choreoId);
    Task<ChoreoDto?> AddLoopAsync(int userId, int choreoId, VideoSegmentDto loop);
    Task<ChoreoDto?> DeleteLoopAsync(int userId, int choreoId, int loopId);
}

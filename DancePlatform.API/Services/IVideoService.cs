using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

public interface IVideoService
{
    Task<List<VideoDto>> GetByDanceAsync(int danceId);
    Task<VideoDto?> GetByIdAsync(int id);
    Task<VideoDto?> CreateAsync(CreateVideoRequest request);
    Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request);
    Task<bool> DeleteAsync(int id);
}

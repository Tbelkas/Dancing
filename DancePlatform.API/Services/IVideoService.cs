using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

public interface IVideoService
{
    Task<List<VideoDto>> GetByDanceAsync(int danceId);
    Task<List<VideoChapterDto>> GetRelatedAsync(int id);
    Task<VideoDto?> GetByIdAsync(int id);
    Task<VideoDto?> CreateAsync(CreateVideoRequest request);
    Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request);
    Task<VideoDto?> AddSegmentAsync(int id, VideoSegmentDto segment);
    Task<VideoDto?> DeleteSegmentAsync(int videoId, int segmentId);
    Task<bool> DeleteAsync(int id);
    Task<bool> IncrementViewCountAsync(int id);
}

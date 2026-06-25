using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

/// <summary>Outcome of reassigning a video to a different dance.</summary>
public enum MoveVideoResult { Success, VideoNotFound, DanceNotFound }

public interface IVideoService
{
    Task<List<VideoDto>> GetByDanceAsync(int danceId, int? userId);
    Task<List<VideoChapterDto>> GetRelatedAsync(int id);
    Task<VideoDto?> GetByIdAsync(int id, int? userId);
    Task<VideoDto?> CreateAsync(CreateVideoRequest request, int? userId);
    Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request, int? userId);
    Task<(MoveVideoResult Result, VideoDto? Video)> MoveToDanceAsync(int id, int danceId, int? userId);
    Task<VideoDto?> AddSegmentAsync(int id, VideoSegmentDto segment, int? userId);
    Task<VideoDto?> DeleteSegmentAsync(int videoId, int segmentId, int? userId);
    Task<bool> DeleteAsync(int id);
    Task<bool> IncrementViewCountAsync(int id);
    Task<VideoDto?> RateVideoAsync(int userId, int videoId, int rating);
}

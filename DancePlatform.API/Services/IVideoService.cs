using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

/// <summary>Outcome of reassigning a video to a different dance.</summary>
public enum MoveVideoResult { Success, VideoNotFound, DanceNotFound }

public interface IVideoService
{
    Task<List<VideoDto>> GetByDanceAsync(int danceId);
    Task<List<VideoChapterDto>> GetRelatedAsync(int id);
    Task<VideoDto?> GetByIdAsync(int id);
    Task<VideoDto?> CreateAsync(CreateVideoRequest request);
    Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request);
    Task<(MoveVideoResult Result, VideoDto? Video)> MoveToDanceAsync(int id, int danceId);
    Task<VideoDto?> AddSegmentAsync(int id, VideoSegmentDto segment);
    Task<VideoDto?> DeleteSegmentAsync(int videoId, int segmentId);
    Task<bool> DeleteAsync(int id);
    Task<bool> IncrementViewCountAsync(int id);
}

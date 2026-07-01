using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

/// <summary>Outcome of reassigning a video to a different dance.</summary>
public enum MoveVideoResult { Success, VideoNotFound, DanceNotFound }

/// <summary>Outcome of a delete: Forbidden when a non-admin tries to delete a video they don't own.</summary>
public enum DeleteVideoResult { Success, NotFound, Forbidden }

public interface IVideoService
{
    Task<List<VideoDto>> GetByDanceAsync(int danceId, int? userId);
    /// <summary>Videos the given user added privately (their personal library).</summary>
    Task<List<VideoLibraryItemDto>> GetMineAsync(int userId);
    /// <summary>All global (curated) videos, newest first — admin library view.</summary>
    Task<List<VideoLibraryItemDto>> GetGlobalAsync();
    Task<List<VideoChapterDto>> GetRelatedAsync(int id, int? userId);
    Task<VideoDto?> GetByIdAsync(int id, int? userId);
    Task<VideoDto?> CreateAsync(CreateVideoRequest request, int? userId, bool isAdmin);
    Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request, int? userId);
    Task<(MoveVideoResult Result, VideoDto? Video)> MoveToDanceAsync(int id, int danceId, int? userId);
    Task<VideoDto?> AddSegmentAsync(int id, VideoSegmentDto segment, int? userId);
    Task<VideoDto?> DeleteSegmentAsync(int videoId, int segmentId, int? userId);
    Task<DeleteVideoResult> DeleteAsync(int id, int? userId, bool isAdmin);
    Task<bool> IncrementViewCountAsync(int id);
    Task<VideoDto?> RateVideoAsync(int userId, int videoId, int rating);
}

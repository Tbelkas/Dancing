using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

/// <summary>Outcome of reassigning a video to a different dance.</summary>
public enum MoveVideoResult { Success, VideoNotFound, DanceNotFound }

/// <summary>Outcome of adding a video: Duplicate when the same clip already exists on the dance.</summary>
public enum CreateVideoResult { Success, DanceNotFound, Duplicate }

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
    /// <param name="honourGate">
    /// When true the intake rubric decides the ReviewState: below the admit threshold the
    /// video lands as "pending" instead of going straight onto the site. Bulk import passes
    /// true; the add-video form passes false, because a person already looked at it.
    /// </param>
    Task<(CreateVideoResult Result, VideoDto? Video)> CreateAsync(CreateVideoRequest request, int? userId, bool isAdmin, bool honourGate = false);
    Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request, int? userId);
    Task<(MoveVideoResult Result, VideoDto? Video)> MoveToDanceAsync(int id, int danceId, int? userId);
    Task<VideoDto?> AddSegmentAsync(int id, VideoSegmentDto segment, int? userId);
    Task<VideoDto?> DeleteSegmentAsync(int videoId, int segmentId, int? userId);
    Task<DeleteVideoResult> DeleteAsync(int id, int? userId, bool isAdmin);
    Task<bool> IncrementViewCountAsync(int id);
    Task<VideoDto?> RateVideoAsync(int userId, int videoId, int rating);
}

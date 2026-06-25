using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

public interface IUserVideoLoopService
{
    /// <summary>The requesting user's saved loops for one video, earliest first.</summary>
    Task<List<UserVideoLoopDto>> GetForVideoAsync(int userId, int videoId);

    /// <summary>Saves a loop for the user; returns the updated list, or null if the
    /// video doesn't exist or the input is invalid.</summary>
    Task<List<UserVideoLoopDto>?> AddAsync(int userId, int videoId, VideoSegmentDto loop);

    /// <summary>Deletes one of the user's own loops; returns the updated list, or null
    /// if no matching loop is owned by the user.</summary>
    Task<List<UserVideoLoopDto>?> DeleteAsync(int userId, int videoId, int loopId);
}

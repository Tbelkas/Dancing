using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

/// <summary>Outcome of a report: Duplicate when this video already has an open flag for the same reason.</summary>
public enum ReportVideoResult { Success, VideoNotFound, Duplicate }

/// <summary>
/// Problem reports on videos — raised by viewers from the video page, and by the nightly
/// availability checker. Read only by the admin flags queue.
/// </summary>
public interface IVideoFlagService
{
    /// <summary>
    /// Files a report. Anonymous callers are allowed (the whole point is that a visitor who spots
    /// a dead embed can say so), which is why the duplicate check is on the video and reason
    /// rather than on the reporter.
    /// </summary>
    Task<ReportVideoResult> ReportAsync(int videoId, ReportVideoRequest request, int? userId, string source = "viewer");

    /// <param name="state">"open" (default) or "resolved".</param>
    Task<List<VideoFlagDto>> GetAsync(string state);

    /// <summary>Closes a flag. Returns null when there is no such flag.</summary>
    Task<VideoFlagDto?> ResolveAsync(int flagId, string? resolution, int? adminUserId);

    /// <summary>Open-flag count for the dashboard headline.</summary>
    Task<int> CountOpenAsync();
}

using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

public interface IYoutubeChapterService
{
    /// <summary>
    /// Reads the chapters a YouTube video already publishes. Returns a result with an empty
    /// chapter list when the video has none or YouTube couldn't be reached — never throws,
    /// because this only ever augments a form the user can still fill in by hand.
    /// </summary>
    Task<YoutubeChaptersDto> GetChaptersAsync(string videoId, CancellationToken ct = default);
}

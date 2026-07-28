namespace DancePlatform.API.DTOs.Video;

/// <summary>
/// The chapters ("chips") a YouTube video already carries, offered as ready-made sections
/// when adding that video. Empty <see cref="Chapters"/> means the video has none.
/// </summary>
public class YoutubeChaptersDto
{
    public string VideoId { get; set; } = string.Empty;
    /// <summary>Video length in seconds, when the page exposed it — bounds the last chapter.</summary>
    public int? Duration { get; set; }
    /// <summary>Where the chapters came from: "chapters" (YouTube's own bar), "description" (timestamp list), or "none".</summary>
    public string Source { get; set; } = "none";
    /// <summary>Chapter list in play order, shaped exactly like the segments a video is created with.</summary>
    public List<VideoSegmentDto> Chapters { get; set; } = new();
}

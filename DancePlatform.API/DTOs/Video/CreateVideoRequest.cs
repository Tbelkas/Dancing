using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Video;

public class CreateVideoRequest
{
    [Required] public string Title { get; set; } = string.Empty;
    [Required] public string VideoId { get; set; } = string.Empty;
    public string Platform { get; set; } = "youtube";
    public string VideoType { get; set; } = "steps";
    public string? Description { get; set; }
    [Required] public int DanceId { get; set; }
    // "global" | "local". Honoured only for admins; non-admins always create personal videos.
    public string? Scope { get; set; }
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }
    public List<VideoSegmentDto> Segments { get; set; } = new();
}

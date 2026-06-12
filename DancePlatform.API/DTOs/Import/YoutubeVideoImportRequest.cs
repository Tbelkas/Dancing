using System.ComponentModel.DataAnnotations;
using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.DTOs.Import;

public class YoutubeVideoImportRequest
{
    [Required] public string YoutubeUrl { get; set; } = string.Empty;
    [Required] public string Title { get; set; } = string.Empty;
    [Required] public int DanceId { get; set; }
    public string VideoType { get; set; } = "steps";
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }
    public List<VideoSegmentDto> Segments { get; set; } = new();
}

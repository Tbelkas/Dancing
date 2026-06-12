using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Video;

public class VideoSegmentDto
{
    public int Id { get; set; }
    [Required] public string Label { get; set; } = string.Empty;
    public int StartTime { get; set; }
    public int? EndTime { get; set; }
}

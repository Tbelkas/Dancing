namespace DancePlatform.API.DTOs.Video;

public class UpdateVideoRequest
{
    public string? Title { get; set; }
    public string? VideoId { get; set; }
    public string? Description { get; set; }
    public string? VideoType { get; set; }
    public bool UpdateTimes { get; set; }
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }
    public bool UpdateSegments { get; set; }
    public List<VideoSegmentDto> Segments { get; set; } = new();
}

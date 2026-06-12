namespace DancePlatform.API.Models;

public class VideoSegment
{
    public int Id { get; set; }
    public string Label { get; set; } = string.Empty;
    public int StartTime { get; set; }
    public int? EndTime { get; set; }

    public int VideoId { get; set; }
    public Video Video { get; set; } = null!;
}

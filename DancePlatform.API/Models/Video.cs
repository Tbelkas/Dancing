namespace DancePlatform.API.Models;

public class Video
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string YouTubeId { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public long ViewCount { get; set; } = 0;
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }

    public int DanceId { get; set; }
    public Dance Dance { get; set; } = null!;
}

namespace DancePlatform.API.DTOs.Video;

public class VideoDto
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string YouTubeId { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; }
    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
}

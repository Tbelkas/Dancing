namespace DancePlatform.API.DTOs.Video;

/// <summary>A video as it appears in the "added videos" library list: enough to render a row,
/// badge its scope, and link back to the dance it lives on.</summary>
public class VideoLibraryItemDto
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string VideoId { get; set; } = string.Empty;
    public string Platform { get; set; } = "youtube";
    public string VideoType { get; set; } = "steps";
    public DateTime DateAdded { get; set; }
    public long ViewCount { get; set; }
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }
    // Null = global (curated); set = personal to that user.
    public int? OwnerUserId { get; set; }
    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
    public string DanceSlug { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;
}

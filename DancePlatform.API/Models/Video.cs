namespace DancePlatform.API.Models;

public class Video
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string VideoId { get; set; } = string.Empty;
    public string Platform { get; set; } = "youtube";
    public string VideoType { get; set; } = "steps";
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public long ViewCount { get; set; } = 0;
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }

    public double AverageRating { get; set; }
    public int RatingCount { get; set; }

    public int DanceId { get; set; }
    public Dance Dance { get; set; } = null!;

    // Null = global (curated, visible to everyone). Set = personal to that user — only the
    // owner sees it on the dance. Mirrors the per-user UserVideoLoop privacy model.
    public int? OwnerUserId { get; set; }
    public User? Owner { get; set; }

    public List<VideoSegment> Segments { get; set; } = new();
    public ICollection<VideoRating> Ratings { get; set; } = new List<VideoRating>();
}

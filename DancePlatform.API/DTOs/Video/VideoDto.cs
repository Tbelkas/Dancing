namespace DancePlatform.API.DTOs.Video;

public class VideoDto
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string VideoId { get; set; } = string.Empty;
    public string Platform { get; set; } = "youtube";
    public string VideoType { get; set; } = "steps";
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; }
    public long ViewCount { get; set; }
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }
    // Full length of the source upload. The UI subtracts StartTime to show how much of it this
    // video actually is - runtime is what you pick on when several videos cover the same move.
    public int? DurationSeconds { get; set; }
    /// <summary>
    /// How many dances are cut from this same source upload, this one included. Above 1 means
    /// the player must stay seekable past this dance's end so the jump chips can reach the
    /// neighbouring sections. The chips themselves arrive on a separate request, too late for
    /// the player to be built around them, so the decision rides along with the video instead.
    /// </summary>
    public int SharedSourceCount { get; set; }
    public double AverageRating { get; set; }
    public int RatingCount { get; set; }
    public int? UserRating { get; set; }
    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
    // Null = global; set = personal to this user. Lets the UI badge personal videos and
    // offer their owner a delete control.
    public int? OwnerUserId { get; set; }
    public List<VideoSegmentDto> Segments { get; set; } = new();
}

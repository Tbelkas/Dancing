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

    /// <summary>Full source-video length in seconds (from yt-dlp metadata); null when unknown.</summary>
    public int? DurationSeconds { get; set; }

    /// <summary>
    /// Who published the source upload, as the platform names them ("blogilates"), and a link
    /// to their channel there. Filled from the platform's oEmbed endpoint on create, and by
    /// scripts/backfill_channels.py for rows that arrived by raw insert. Null = not looked up
    /// yet, or the platform has no public lookup (Instagram).
    /// </summary>
    public string? ChannelName { get; set; }
    public string? ChannelUrl { get; set; }

    // --- Intake quality gate ---------------------------------------------
    // Bulk-seeded videos land as "pending" and are held out of every public
    // query by the global filter in AppDbContext until someone reviews them.
    // That filter is deliberately global rather than a Where() per call site:
    // DanceService, RoadmapService and PracticeService all read Dance.Videos
    // directly, and a hand-written predicate would eventually miss one and
    // leak a quarantined video onto the site.
    //
    // Videos added by hand through the admin form go straight to "approved" —
    // someone has already looked at them — but still carry a score and flags
    // so a bad one can be found later.
    //
    //   approved  visible; the default and what every existing row backfills to
    //   pending   held back, waiting on review
    //   rejected  held back, reviewed and refused
    public string ReviewState { get; set; } = "approved";
    public float? QualityScore { get; set; }
    public string? QualityFlags { get; set; }
    public DateTime? ReviewedAt { get; set; }
    public string? ReviewNote { get; set; }

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

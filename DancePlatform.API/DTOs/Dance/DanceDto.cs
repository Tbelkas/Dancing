namespace DancePlatform.API.DTOs.Dance;

public class DanceDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    /// <summary>Slug of the canonical style, for building the /dances/{styleSlug}/{slug} URL.</summary>
    public string StyleSlug { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; }
    public string Difficulty { get; set; } = "None";
    public List<string> Styles { get; set; } = new();
    public List<string> MusicalStyles { get; set; } = new();
    public List<string> Instructors { get; set; } = new();
    public int VideoCount { get; set; }

    /// <summary>Total watchable seconds across this dance's visible videos (clip windows honoured); 0 when unknown.</summary>
    public int TotalDurationSeconds { get; set; }
    public string? ThumbnailVideoId { get; set; }
    public string? ThumbnailPlatform { get; set; }
    public int FavoriteCount { get; set; }
    public int LearnedCount { get; set; }
    public double AverageRating { get; set; }
    public int RatingCount { get; set; }
    public bool IsFavorite { get; set; }
    public bool IsLearned { get; set; }
    public bool IsInProgress { get; set; }

    /// <summary>"approved" (in the public catalogue) or "pending" (awaiting review). A caller only
    /// ever sees "pending" on a dance they added themselves, or as an admin.</summary>
    public string ReviewState { get; set; } = "approved";

    /// <summary>Who added it, when that was a user rather than the seeded catalogue. Present so the
    /// review queue can say whose submission it is.</summary>
    public int? OwnerUserId { get; set; }
}

using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace DancePlatform.API.DTOs.Video;

/// <summary>
/// A video held back by the intake gate, as the review queue needs it: enough to play the clip,
/// read the rubric's objection, and see what it would be published onto.
/// </summary>
public class PendingVideoDto
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
    public int? DurationSeconds { get; set; }

    public string ReviewState { get; set; } = "pending";
    /// <summary>The rubric's score, 0-1. Null when the row predates the gate.</summary>
    public float? QualityScore { get; set; }
    /// <summary>The rubric's objections, split from the comma-joined column for display.</summary>
    public List<string> QualityFlags { get; set; } = new();
    /// <summary>The raw comma-joined column, split into <see cref="QualityFlags"/> after the
    /// query materializes. Not part of the wire shape.</summary>
    [JsonIgnore] public string? RawFlags { get; set; }
    public DateTime? ReviewedAt { get; set; }
    public string? ReviewNote { get; set; }

    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
    public string DanceSlug { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;

    /// <summary>
    /// How much rides on the decision: favourites on the target dance, which is the closest
    /// thing to "people will see this". Drives the queue order so the videos that matter get
    /// judged while the reviewer is still fresh.
    /// </summary>
    public int DanceFavoriteCount { get; set; }
    /// <summary>Approved videos already on the target dance — a dance with none needs this one more.</summary>
    public int DanceVideoCount { get; set; }
    public List<VideoSegmentDto> Segments { get; set; } = new();
}

/// <summary>Approve or reject a held-back video, optionally recording why.</summary>
public class ReviewVideoRequest
{
    /// <summary>"approved" publishes it; "rejected" keeps it held back, reviewed and refused.</summary>
    [Required]
    [RegularExpression("^(approved|rejected|pending)$",
        ErrorMessage = "Review state must be approved, rejected, or pending.")]
    public string ReviewState { get; set; } = string.Empty;

    [MaxLength(500)] public string? Note { get; set; }
}

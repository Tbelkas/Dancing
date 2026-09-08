using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Video;

/// <summary>An open (or closed) problem report, as the admin flags queue renders it.</summary>
public class VideoFlagDto
{
    public int Id { get; set; }
    public string Reason { get; set; } = string.Empty;
    /// <summary>The reason in words, so the queue doesn't make the reader decode slugs.</summary>
    public string ReasonLabel { get; set; } = string.Empty;
    public string? Detail { get; set; }
    /// <summary>"viewer" or "checker" — a dead link found by the nightly job reads differently.</summary>
    public string Source { get; set; } = "viewer";
    public int? ReportedByUserId { get; set; }
    public string? ReportedByUsername { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? ResolvedAt { get; set; }
    public string? Resolution { get; set; }

    public int VideoId { get; set; }
    public string VideoTitle { get; set; } = string.Empty;
    public string SourceVideoId { get; set; } = string.Empty;
    public string Platform { get; set; } = "youtube";
    /// <summary>Whether the video is still on the site — a quarantined one needs no fixing.</summary>
    public string VideoReviewState { get; set; } = "approved";

    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
    public string DanceSlug { get; set; } = string.Empty;
    public string StyleSlug { get; set; } = string.Empty;
    /// <summary>Other open reports on the same video — three people saying it is dead is a fact.</summary>
    public int OpenFlagsOnVideo { get; set; }
}

/// <summary>A viewer (or the link checker) reporting a problem with a video.</summary>
public class ReportVideoRequest
{
    /// <summary>One of the fixed reasons; anything else is refused so the queue stays groupable.</summary>
    [Required]
    [RegularExpression("^(dead-video|wrong-dance|bad-sections|wrong-timing|other)$",
        ErrorMessage = "Pick one of the listed reasons.")]
    public string Reason { get; set; } = string.Empty;

    [MaxLength(500)] public string? Detail { get; set; }
}

/// <summary>Closing a flag: what was done about it.</summary>
public class ResolveFlagRequest
{
    [MaxLength(200)] public string? Resolution { get; set; }
}

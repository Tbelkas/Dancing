namespace DancePlatform.API.Models;

/// <summary>
/// A report that something is wrong with a video: raised by a viewer from the video page, or by
/// the link checker when a source upload stops resolving.
///
/// One table for both on purpose. A dead embed and a mis-filed clip are the same job for whoever
/// clears them — open it, look, fix or dismiss — and splitting them would mean two queues, two
/// pages, and one of them going unread.
///
/// Deliberately NOT carrying the Video query filter: a flag on a video that has since been
/// quarantined is exactly the flag most worth seeing, and the admin queue is the only thing that
/// reads this table.
/// </summary>
public class VideoFlag
{
    public int Id { get; set; }

    public int VideoId { get; set; }
    public Video Video { get; set; } = null!;

    /// <summary>
    /// What is wrong, from a fixed set so the queue can be grouped and counted:
    /// "dead-video", "wrong-dance", "bad-sections", "wrong-timing", "other".
    /// </summary>
    public string Reason { get; set; } = string.Empty;

    /// <summary>The reporter's own words, when they added any. Capped in the DTO, not here.</summary>
    public string? Detail { get; set; }

    /// <summary>"viewer" (someone on the site) or "checker" (the nightly availability job).</summary>
    public string Source { get; set; } = "viewer";

    /// <summary>Who reported it, when they were signed in. Null for anonymous and for the checker.</summary>
    public int? ReportedByUserId { get; set; }
    public User? ReportedBy { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>Null while the flag is open. Set once someone has dealt with it either way.</summary>
    public DateTime? ResolvedAt { get; set; }
    public int? ResolvedByUserId { get; set; }
    public User? ResolvedBy { get; set; }

    /// <summary>What was done about it — "fixed", "dismissed", or a note.</summary>
    public string? Resolution { get; set; }
}

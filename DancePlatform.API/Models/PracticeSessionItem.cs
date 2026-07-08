namespace DancePlatform.API.Models;

/// <summary>
/// One thing practiced within a <see cref="PracticeSession"/>, with accumulated watch time —
/// either a dance (catalog video) or one of the user's local choreos, never both.
/// </summary>
public class PracticeSessionItem
{
    public int Id { get; set; }
    public int PracticeSessionId { get; set; }

    /// <summary>The dance practiced; null when the time came from a local choreo instead.</summary>
    public int? DanceId { get; set; }

    /// <summary>
    /// The video that generated the watch time, so history can be reattributed if a video is
    /// later moved to another dance. Null for manual log entries and pre-existing rows.
    /// </summary>
    public int? VideoId { get; set; }

    /// <summary>The local choreo practiced; null for dance items. Nulled if the choreo is removed.</summary>
    public int? UserChoreoId { get; set; }

    /// <summary>Total seconds of video watched for this dance/choreo in the session.</summary>
    public int Seconds { get; set; }

    public string? Notes { get; set; }

    public PracticeSession Session { get; set; } = null!;
    public Dance? Dance { get; set; }
    public Video? Video { get; set; }
    public UserChoreo? Choreo { get; set; }
}

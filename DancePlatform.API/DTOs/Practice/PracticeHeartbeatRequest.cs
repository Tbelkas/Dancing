using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Practice;

/// <summary>
/// Sent periodically by the player while a video is playing. <see cref="Seconds"/> is the watch
/// time accumulated since the last beat; the server folds it into the live session (or starts a
/// new one once the continuation buffer has lapsed).
/// </summary>
public class PracticeHeartbeatRequest
{
    [Required] public int DanceId { get; set; }

    /// <summary>Watch seconds since the previous heartbeat.</summary>
    [Range(1, 600)] public int Seconds { get; set; }

    /// <summary>Client's local date, so streaks line up with the user's calendar day.</summary>
    [Required] public DateOnly LocalDate { get; set; }
}

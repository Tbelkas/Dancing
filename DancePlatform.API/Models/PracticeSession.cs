namespace DancePlatform.API.Models;

/// <summary>
/// A windowed practice session. Time accumulates while the user watches videos; watches
/// that land within the continuation buffer (10 min of <see cref="LastActivityAt"/>) extend
/// the same session, so one session can cover several dances. <see cref="Items"/> records
/// what was practiced and for how long.
/// </summary>
public class PracticeSession
{
    public int Id { get; set; }
    public int UserId { get; set; }

    /// <summary>Local calendar date the session belongs to (for streaks/grouping).</summary>
    public DateOnly Date { get; set; }

    public DateTime StartedAt { get; set; } = DateTime.UtcNow;

    /// <summary>Last time activity was recorded; drives the 10-minute continuation buffer.</summary>
    public DateTime LastActivityAt { get; set; } = DateTime.UtcNow;

    public string? Notes { get; set; }

    public User User { get; set; } = null!;
    public ICollection<PracticeSessionItem> Items { get; set; } = new List<PracticeSessionItem>();
}

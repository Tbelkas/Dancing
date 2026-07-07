namespace DancePlatform.API.Models;

/// <summary>
/// A saved time slot (loop region) on a user's local choreo video — the only playback
/// state persisted for a <see cref="UserChoreo"/>, since the video stays on their disk.
/// </summary>
public class UserChoreoLoop
{
    public int Id { get; set; }

    public int UserChoreoId { get; set; }
    public UserChoreo Choreo { get; set; } = null!;

    public string Label { get; set; } = string.Empty;
    public int StartTime { get; set; }
    public int EndTime { get; set; }

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;
}

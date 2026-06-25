namespace DancePlatform.API.Models;

/// <summary>
/// A loop region a user saved for their own account on a specific video. Unlike
/// <see cref="VideoSegment"/> (global sections curated by admins, visible to
/// everyone), these are private to the owning user.
/// </summary>
public class UserVideoLoop
{
    public int Id { get; set; }

    public int UserId { get; set; }
    public User User { get; set; } = null!;

    public int VideoId { get; set; }
    public Video Video { get; set; } = null!;

    public string Label { get; set; } = string.Empty;
    public int StartTime { get; set; }
    public int? EndTime { get; set; }

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;
}

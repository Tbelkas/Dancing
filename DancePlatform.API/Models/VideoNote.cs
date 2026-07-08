namespace DancePlatform.API.Models;

/// <summary>
/// A timestamped personal note a user pinned to a moment in a video
/// ("2:34 — weight stays on the left foot"). Private to the owning user,
/// like <see cref="UserVideoLoop"/>; unlike loops it marks a point, not a range.
/// </summary>
public class VideoNote
{
    public int Id { get; set; }

    public int UserId { get; set; }
    public User User { get; set; } = null!;

    public int VideoId { get; set; }
    public Video Video { get; set; } = null!;

    public int TimeSeconds { get; set; }
    public string Text { get; set; } = string.Empty;

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;
}

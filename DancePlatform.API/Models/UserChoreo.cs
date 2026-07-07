namespace DancePlatform.API.Models;

/// <summary>
/// A choreography video that lives on the user's own computer. The file itself is
/// never uploaded — we keep only its file name (so the UI can ask for the same file
/// again) and the loop regions the user saved for it.
/// </summary>
public class UserChoreo
{
    public int Id { get; set; }

    public int UserId { get; set; }
    public User User { get; set; } = null!;

    /// <summary>Display title, defaults to the file name without extension.</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>Original file name, used to re-match the local file on later visits.</summary>
    public string FileName { get; set; } = string.Empty;

    /// <summary>Captured from the video metadata on first play; display only.</summary>
    public int? DurationSeconds { get; set; }

    /// <summary>Clockwise playback rotation (0, 90, 180 or 270) for sideways phone recordings.</summary>
    public int RotationDegrees { get; set; }

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public List<UserChoreoLoop> Loops { get; set; } = new();
}

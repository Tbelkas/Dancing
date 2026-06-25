namespace DancePlatform.API.Models;

/// <summary>One dance practiced within a <see cref="PracticeSession"/>, with accumulated watch time.</summary>
public class PracticeSessionItem
{
    public int Id { get; set; }
    public int PracticeSessionId { get; set; }
    public int DanceId { get; set; }

    /// <summary>Total seconds of video watched for this dance in the session.</summary>
    public int Seconds { get; set; }

    public string? Notes { get; set; }

    public PracticeSession Session { get; set; } = null!;
    public Dance Dance { get; set; } = null!;
}

namespace DancePlatform.API.DTOs.Practice;

public class PracticeSessionDto
{
    public int Id { get; set; }
    public DateOnly Date { get; set; }
    public DateTime StartedAt { get; set; }
    public DateTime LastActivityAt { get; set; }
    public string? Notes { get; set; }

    /// <summary>Total practice time across all dances in the session.</summary>
    public int TotalSeconds { get; set; }
    public int DurationMinutes { get; set; }

    public List<PracticeSessionItemDto> Items { get; set; } = new();
}

public class PracticeSessionItemDto
{
    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
    public string DanceSlug { get; set; } = string.Empty;
    public string DanceStyleSlug { get; set; } = string.Empty;
    public int Seconds { get; set; }
    public int Minutes { get; set; }
    public string? Notes { get; set; }
}

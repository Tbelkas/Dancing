namespace DancePlatform.API.DTOs.Practice;

public class PracticeSessionDto
{
    public int Id { get; set; }
    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
    public string DanceSlug { get; set; } = string.Empty;
    public string DanceStyleSlug { get; set; } = string.Empty;
    public DateOnly Date { get; set; }
    public int? DurationMinutes { get; set; }
    public string? Notes { get; set; }
}

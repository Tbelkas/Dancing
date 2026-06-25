using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Practice;

/// <summary>Manual log entry: creates a standalone session with a single dance.</summary>
public class CreatePracticeSessionRequest
{
    [Required] public int DanceId { get; set; }
    [Required] public DateOnly Date { get; set; }
    public int? DurationMinutes { get; set; }
    public string? Notes { get; set; }
}

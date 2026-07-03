using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Practice;

/// <summary>Edits an existing session: date, notes, and (for single-dance sessions) duration.</summary>
public class UpdatePracticeSessionRequest
{
    [Required] public DateOnly Date { get; set; }
    public string? Notes { get; set; }

    /// <summary>New total duration in minutes; only applied when the session has exactly one dance.</summary>
    public int? DurationMinutes { get; set; }
}

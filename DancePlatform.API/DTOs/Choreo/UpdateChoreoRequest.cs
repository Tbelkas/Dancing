using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Choreo;

public class UpdateChoreoRequest
{
    [MaxLength(200)] public string? Name { get; set; }
    /// <summary>Set when the user re-links a differently named file so future visits ask for the right one.</summary>
    [MaxLength(300)] public string? FileName { get; set; }
    public int? DurationSeconds { get; set; }
}

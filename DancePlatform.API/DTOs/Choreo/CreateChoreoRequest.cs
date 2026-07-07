using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Choreo;

public class CreateChoreoRequest
{
    [Required, MaxLength(200)] public string Name { get; set; } = string.Empty;
    [Required, MaxLength(300)] public string FileName { get; set; } = string.Empty;
    public int? DurationSeconds { get; set; }
}

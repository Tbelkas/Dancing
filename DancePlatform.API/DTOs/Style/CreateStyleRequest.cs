using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Style;

public class CreateStyleRequest
{
    [Required, MinLength(2)] public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
}

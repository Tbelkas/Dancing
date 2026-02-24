using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.MusicalStyle;

public class CreateMusicalStyleRequest
{
    [Required, MinLength(2)] public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
}

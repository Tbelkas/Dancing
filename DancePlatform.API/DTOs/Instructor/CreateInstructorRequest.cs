using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Instructor;

public class CreateInstructorRequest
{
    [Required, MinLength(2)] public string Name { get; set; } = string.Empty;
    public string? Bio { get; set; }
    public string? AvatarUrl { get; set; }
    public string? Website { get; set; }
}

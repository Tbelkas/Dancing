namespace DancePlatform.API.DTOs.Instructor;

public class InstructorDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Bio { get; set; }
    public string? AvatarUrl { get; set; }
    public string? Website { get; set; }
    public int DanceCount { get; set; }
}

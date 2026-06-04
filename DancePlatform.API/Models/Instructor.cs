namespace DancePlatform.API.Models;

public class Instructor
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Bio { get; set; }
    public string? AvatarUrl { get; set; }
    public string? Website { get; set; }

    public ICollection<DanceInstructor> DanceInstructors { get; set; } = new List<DanceInstructor>();
}

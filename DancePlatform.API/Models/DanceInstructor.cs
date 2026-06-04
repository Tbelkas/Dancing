namespace DancePlatform.API.Models;

public class DanceInstructor
{
    public int DanceId { get; set; }
    public int InstructorId { get; set; }

    public Dance Dance { get; set; } = null!;
    public Instructor Instructor { get; set; } = null!;
}

namespace DancePlatform.API.Models;

public class PracticeSession
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public int DanceId { get; set; }
    public DateOnly Date { get; set; }
    public int? DurationMinutes { get; set; }
    public string? Notes { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public User User { get; set; } = null!;
    public Dance Dance { get; set; } = null!;
}

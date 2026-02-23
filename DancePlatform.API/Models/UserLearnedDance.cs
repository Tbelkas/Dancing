namespace DancePlatform.API.Models;

public class UserLearnedDance
{
    public int UserId { get; set; }
    public User User { get; set; } = null!;

    public int DanceId { get; set; }
    public Dance Dance { get; set; } = null!;

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;
}

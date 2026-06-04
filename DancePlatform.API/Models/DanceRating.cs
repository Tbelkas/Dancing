namespace DancePlatform.API.Models;

public class DanceRating
{
    public int UserId { get; set; }
    public int DanceId { get; set; }
    public int Rating { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public User User { get; set; } = null!;
    public Dance Dance { get; set; } = null!;
}

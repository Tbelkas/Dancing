namespace DancePlatform.API.Models;

public class VideoRating
{
    public int UserId { get; set; }
    public int VideoId { get; set; }
    public int Rating { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public User User { get; set; } = null!;
    public Video Video { get; set; } = null!;
}

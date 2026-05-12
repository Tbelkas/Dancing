namespace DancePlatform.API.Models;

public class UserMyStyle
{
    public int UserId { get; set; }
    public User User { get; set; } = null!;

    public int StyleId { get; set; }
    public Style Style { get; set; } = null!;

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;
}

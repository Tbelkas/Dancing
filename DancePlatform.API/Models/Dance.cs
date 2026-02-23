namespace DancePlatform.API.Models;

public class Dance
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public ICollection<DanceStyle> DanceStyles { get; set; } = new List<DanceStyle>();
    public ICollection<Video> Videos { get; set; } = new List<Video>();
    public ICollection<UserFavoriteDance> FavoritedBy { get; set; } = new List<UserFavoriteDance>();
    public ICollection<UserLearnedDance> LearnedBy { get; set; } = new List<UserLearnedDance>();
}

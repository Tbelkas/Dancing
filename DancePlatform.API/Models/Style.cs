namespace DancePlatform.API.Models;

public class Style
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public ICollection<DanceStyle> DanceStyles { get; set; } = new List<DanceStyle>();
}

namespace DancePlatform.API.DTOs.Dance;

public class DanceDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; }
    public List<string> Styles { get; set; } = new();
    public List<string> MusicalStyles { get; set; } = new();
    public int VideoCount { get; set; }
    public bool IsFavorite { get; set; }
    public bool IsLearned { get; set; }
}

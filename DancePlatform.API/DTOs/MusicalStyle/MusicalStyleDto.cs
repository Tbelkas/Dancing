namespace DancePlatform.API.DTOs.MusicalStyle;

public class MusicalStyleDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; }
    public int DanceCount { get; set; }
}

namespace DancePlatform.API.DTOs.Style;

public class StyleDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; }
    public int DanceCount { get; set; }
}

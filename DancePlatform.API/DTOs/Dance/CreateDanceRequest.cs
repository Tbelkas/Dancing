using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Dance;

public class CreateDanceRequest
{
    [Required, MinLength(2)] public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public List<int> StyleIds { get; set; } = new();
    public List<int> MusicalStyleIds { get; set; } = new();
}
